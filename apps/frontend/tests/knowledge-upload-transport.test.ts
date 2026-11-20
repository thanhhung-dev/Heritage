import assert from "node:assert/strict";
import test from "node:test";
import { createDirectUpload, R2TransferError } from "../features/knowledge/upload-transport";
import { uploadFileType } from "../features/knowledge/file-policy";
import type { KnowledgeUploadTicket } from "../features/knowledge/types";

const ticket: KnowledgeUploadTicket = { uploadId: "synthetic-id", objectKey: "folder/note.md", uploadUrl: "https://r2.example.invalid/staging",
  method: "PUT", expiresIn: 300, sessionExpiresAt: "2099-01-01T00:00:00Z",
  requiredHeaders: { "Content-Type": "text/markdown", "If-None-Match": "*", "x-amz-meta-upload-id": "synthetic-id" } };

class FakeXHR {
  status = 200;
  upload: { onprogress: ((event: ProgressEvent) => void) | null } = { onprogress: null };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onabort: (() => void) | null = null;
  ontimeout: (() => void) | null = null;
  withCredentials = true;
  timeout = 0;
  headers: Record<string, string> = {};
  body: unknown;
  method = "";
  open(method: string) { this.method = method; }
  setRequestHeader(name: string, value: string) { this.headers[name] = value; }
  send(body: unknown) { this.body = body; }
  abort() { this.onabort?.(); }
}

test("direct PUT sends raw File and every signed header without bearer auth or Content-Length", async () => {
  const xhr = new FakeXHR();
  const file = new File(["hello"], "note.md", { type: "incorrect/browser-type" });
  const progress: number[] = [];
  const transfer = createDirectUpload(() => xhr as unknown as XMLHttpRequest);
  const pending = transfer(ticket, file, new AbortController().signal, p => progress.push(p.loaded / p.total));
  assert.equal(xhr.body, file);
  assert.equal(xhr.method, "PUT");
  assert.deepEqual(xhr.headers, ticket.requiredHeaders);
  assert.equal(xhr.withCredentials, false);
  xhr.upload.onprogress?.({ loaded: 3, total: 5, lengthComputable: true } as ProgressEvent);
  assert.deepEqual(progress, [0.6]);
  xhr.onload?.();
  await pending;
  assert.equal(xhr.upload.onprogress, null);
  assert.equal(xhr.onload, null);
});

test("staging 412 permits verification; network errors and cancellation clean listeners", async () => {
  for (const mode of ["exists", "network", "cancel"] as const) {
    const xhr = new FakeXHR(); const abort = new AbortController();
    const promise = createDirectUpload(() => xhr as unknown as XMLHttpRequest)(ticket, new File(["x"], "note.md"), abort.signal, () => {});
    if (mode === "exists") { xhr.status = 412; xhr.onload?.(); await promise; }
    if (mode === "network") { xhr.onerror?.(); await assert.rejects(promise, R2TransferError); }
    if (mode === "cancel") { abort.abort(); await assert.rejects(promise, (e: unknown) => e instanceof Error && e.name === "AbortError"); }
    assert.equal(xhr.onload, null); assert.equal(xhr.upload.onprogress, null);
  }
});

test("invalid signing headers fail closed and frontend MIME policy follows backend extensions", async () => {
  await assert.rejects(createDirectUpload()({ ...ticket, requiredHeaders: { Authorization: "must-not-send" } },
    new File(["x"], "x.md"), new AbortController().signal, () => {}), R2TransferError);
  assert.equal(uploadFileType(new File(["x"], "Việt Nam.MD", { type: "" })), "text/markdown");
  assert.equal(uploadFileType(new File(["{}"], "x.json")), "application/json");
  for (const file of [new File(["x"], "x.pdf"), new File([], "x.txt"), new File(["x"], "../x.md"),
      { name: "x.txt", size: 10485761 }, new File(["x"], "việt.md")]) {
    assert.throws(() => uploadFileType(file));
  }
});
