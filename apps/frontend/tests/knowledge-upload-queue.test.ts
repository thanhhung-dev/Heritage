import assert from "node:assert/strict";
import test from "node:test";
import { KnowledgeUploadQueue } from "../features/knowledge/upload-queue";
import { createKnowledgeApi } from "../services/knowledge.service";
import { R2TransferError, type DirectUpload } from "../features/knowledge/upload-transport";
import type { KnowledgeCompletion, KnowledgeUploadTicket } from "../features/knowledge/types";

function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(r => { resolve = r; }); return { promise, resolve }; }
async function settle(queue: KnowledgeUploadQueue) {
  for (let i = 0; i < 100; i++) {
    if (queue.getSnapshot().every(row => ["stored", "failed", "cancelled"].includes(row.state))) return;
    await new Promise(resolve => setTimeout(resolve, 1));
  }
  assert.fail("Queue did not reach a terminal state");
}
function fixture(overrides: { complete?: (id: string) => Response | Promise<Response>; begin?: (signal?: AbortSignal | null) => Response | Promise<Response> } = {}) {
  const calls: string[] = []; let count = 0;
  const tickets = new Map<string, KnowledgeUploadTicket>();
  const result = (id: string): KnowledgeCompletion => {
    const ticket = tickets.get(id)!;
    return { uploadId: id, status: "stored", object: { bucket: "knowledge-heritage", key: ticket.objectKey,
      name: ticket.objectKey.split("/").pop()!, size: 5, contentType: "text/markdown", metadata: {}, etag: '"test"', lastModified: "2026-11-20T00:00:00Z" } };
  };
  const api = createKnowledgeApi({ getToken: () => "synthetic-admin", randomUUID: () => "test", fetchImpl: async (url, init) => {
    const path = new URL(String(url)).pathname;
    if (path.endsWith("/upload-url")) {
      calls.push("begin");
      if (overrides.begin) return overrides.begin(init?.signal);
      const data = JSON.parse(String(init?.body)) as { folder: string; filename: string; contentType: string };
      const ticket: KnowledgeUploadTicket = { uploadId: "id-" + ++count, objectKey: data.folder + data.filename,
        uploadUrl: "https://r2.example.invalid/temporary", method: "PUT", requiredHeaders: {
          "Content-Type": data.contentType, "If-None-Match": "*", "x-amz-meta-upload-id": "id-" + count },
        expiresIn: 300, sessionExpiresAt: "2099-01-01T00:00:00Z" };
      tickets.set(ticket.uploadId, ticket); return Response.json(ticket);
    }
    const id = path.split("/").at(-2)!;
    calls.push("complete:" + id);
    return overrides.complete?.(id) ?? Response.json(result(id));
  } });
  return { api, calls, result };
}

test("upload state machine keeps 100% transfer separate from verified storage and suppresses duplicate starts", async () => {
  const completion = deferred<Response>(); const f = fixture({ complete: () => completion.promise });
  const progress: string[] = [];
  const queue = new KnowledgeUploadQueue(f.api, async (_ticket, file, _signal, report) => {
    f.calls.push("put"); report({ loaded: file.size, total: file.size });
  });
  queue.subscribe(() => progress.push(queue.getSnapshot()[0].state));
  assert.deepEqual(queue.add([new File(["hello"], "note.md")], "area/"), []);
  queue.start(); queue.start(); queue.start();
  for (let i = 0; i < 20 && queue.getSnapshot()[0].state !== "verifying"; i++) await new Promise(r => setTimeout(r, 1));
  assert.equal(queue.getSnapshot()[0].state, "verifying");
  assert.equal(queue.getSnapshot()[0].loaded, 5);
  assert.equal(queue.cancel(queue.getSnapshot()[0].id), false);
  completion.resolve(Response.json(f.result("id-1")));
  await settle(queue);
  assert.equal(queue.getSnapshot()[0].state, "stored");
  assert.deepEqual(f.calls, ["begin", "put", "complete:id-1"]);
  assert.equal(progress.includes("preparing"), true); assert.equal(progress.includes("uploading"), true);
  assert.equal(JSON.stringify(queue.getSnapshot()).includes("uploadUrl"), false);
  queue.dispose();
});

test("lost PUT response retries completion of the same durable session without overwriting staging", async () => {
  const f = fixture(); let puts = 0;
  const queue = new KnowledgeUploadQueue(f.api, async () => { puts++; throw new R2TransferError("Lost response", 0); });
  queue.add([new File(["hello"], "note.md")], "area/"); queue.start(); await settle(queue);
  assert.equal(queue.getSnapshot()[0].state, "failed");
  queue.retry(queue.getSnapshot()[0].id); await settle(queue);
  assert.equal(queue.getSnapshot()[0].state, "stored"); assert.equal(puts, 1);
  assert.deepEqual(f.calls, ["begin", "complete:id-1"]);
  queue.dispose();
});

test("missing staging retries the original valid URL, while an expired unpublished session requests a new ticket", async () => {
  for (const status of [404, 410]) {
    let retries = 0;
    const f = fixture({ complete: id => ++retries === 1 ? new Response("{}", { status }) : Response.json(f.result(id)) });
    let puts = 0;
    const queue = new KnowledgeUploadQueue(f.api, async () => { if (++puts === 1) throw new R2TransferError("Lost transfer", 0); });
    queue.add([new File(["hello"], "note.md")], "area/"); queue.start(); await settle(queue);
    queue.retry(queue.getSnapshot()[0].id); await settle(queue);
    assert.equal(queue.getSnapshot()[0].state, "stored");
    assert.equal(f.calls.filter(c => c === "begin").length, status === 410 ? 2 : 1);
    assert.equal(puts, 2); queue.dispose();
  }
});

test("completion 503 retries verification with the same ID and never uploads twice", async () => {
  let attempts = 0; let puts = 0;
  const f = fixture({ complete: id => ++attempts === 1 ? new Response("{}", { status: 503 }) : Response.json(f.result(id)) });
  const queue = new KnowledgeUploadQueue(f.api, async () => { puts++; });
  queue.add([new File(["hello"], "note.md")], "area/"); queue.start(); await settle(queue);
  queue.retry(queue.getSnapshot()[0].id); await settle(queue);
  assert.equal(queue.getSnapshot()[0].state, "stored"); assert.equal(puts, 1);
  assert.deepEqual(f.calls, ["begin", "complete:id-1", "complete:id-1"]); queue.dispose();
});

test("queue bounds concurrency, preserves each destination and continues after individual failures", async () => {
  const f = fixture(); let active = 0; let maximum = 0;
  const direct: DirectUpload = async (_ticket, file) => {
    active++; maximum = Math.max(maximum, active);
    await new Promise(r => setTimeout(r, 3)); active--;
    if (file.name === "bad.md") throw new R2TransferError("failed file", 0);
  };
  const queue = new KnowledgeUploadQueue(f.api, direct, { concurrency: 2 });
  queue.add([new File(["hello"], "first.md"), new File(["hello"], "bad.md")], "first/");
  queue.add([new File(["hello"], "last.md")], "second/");
  queue.start(); await settle(queue);
  assert.equal(maximum, 2);
  assert.deepEqual(queue.getSnapshot().map(e => [e.folder, e.state]), [["first/", "stored"], ["first/", "failed"], ["second/", "stored"]]);
  queue.dispose();
});

test("cancelled queued files do not call backend and active cancellation does not block the next file", async () => {
  const f = fixture(); const started = deferred<void>();
  const queue = new KnowledgeUploadQueue(f.api, async (_ticket, file, signal) => {
    if (file.name !== "active.md") return;
    started.resolve(); await new Promise<void>((_resolve, reject) => signal.addEventListener("abort", () => reject(new DOMException("cancelled", "AbortError")), { once: true }));
  }, { concurrency: 1 });
  queue.add([new File(["hello"], "active.md"), new File(["hello"], "cancel.md"), new File(["hello"], "next.md")], "area/");
  const ids = queue.getSnapshot().map(e => e.id);
  queue.cancel(ids[1]); queue.start(); await started.promise; queue.cancel(ids[0]); await settle(queue);
  assert.deepEqual(queue.getSnapshot().map(e => e.state), ["cancelled", "cancelled", "stored"]);
  assert.equal(f.calls.filter(c => c === "begin").length, 2); queue.dispose();
});

test("expired URL with missing staging explains the reservation instead of creating duplicate sessions", async () => {
  const f = fixture({ complete: () => new Response("{}", { status: 404 }) }); let now = 0;
  const queue = new KnowledgeUploadQueue(f.api, async () => { throw new R2TransferError("network", 0); }, { now: () => now });
  queue.add([new File(["hello"], "note.md")], "area/"); queue.start(); await settle(queue);
  now = 300_001; queue.retry(queue.getSnapshot()[0].id); await settle(queue);
  assert.equal(queue.getSnapshot()[0].state, "failed");
  assert.match(queue.getSnapshot()[0].error ?? "", /session expires/);
  assert.equal(f.calls.filter(c => c === "begin").length, 1); queue.dispose();
});

test("cancelling session preparation learns its durable ID without sending bytes and retry reuses that ID", async () => {
  const begin = deferred<Response>(); let requestSignal: AbortSignal | null | undefined;
  const ticket: KnowledgeUploadTicket = { uploadId: "reserved-session", objectKey: "area/note.md", method: "PUT",
    uploadUrl: "https://r2.example.invalid/temporary", requiredHeaders: { "Content-Type": "text/markdown", "If-None-Match": "*", "x-amz-meta-upload-id": "reserved-session" }, expiresIn: 300,
    sessionExpiresAt: "2099-01-01T00:00:00Z" };
  let completionAttempts = 0; let puts = 0;
  const f = fixture({ begin: signal => { requestSignal = signal; return begin.promise; }, complete: id => {
    assert.equal(id, ticket.uploadId);
    if (++completionAttempts === 1) return new Response("{}", { status: 404 });
    return Response.json({ uploadId: id, status: "stored", object: { bucket: "knowledge-heritage", key: ticket.objectKey,
      name: "note.md", size: 5, contentType: "text/markdown", metadata: {}, etag: '"test"', lastModified: "2026-11-20T00:00:00Z" } });
  } });
  const queue = new KnowledgeUploadQueue(f.api, async () => { puts++; });
  const file = new File(["hello"], "note.md");
  queue.add([file], "area/"); queue.start();
  const id = queue.getSnapshot()[0].id;
  assert.equal(queue.getSnapshot()[0].state, "preparing");
  assert.equal(queue.cancel(id), true);
  assert.equal(requestSignal?.aborted, false);
  assert.equal(queue.add([file], "area/").length, 1);
  begin.resolve(Response.json(ticket));
  for (let i = 0; i < 100 && !queue.getSnapshot()[0].error?.includes("Retry checks"); i++) await new Promise(r => setTimeout(r, 1));
  assert.equal(puts, 0);
  assert.equal(queue.getSnapshot()[0].state, "cancelled");
  queue.retry(id); await settle(queue);
  assert.equal(queue.getSnapshot()[0].state, "stored");
  assert.equal(puts, 1);
  assert.deepEqual(f.calls, ["begin", "complete:reserved-session", "complete:reserved-session"]);
  queue.dispose();
});
