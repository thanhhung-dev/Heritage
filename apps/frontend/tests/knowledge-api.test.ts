import assert from "node:assert/strict";
import test from "node:test";
import { createKnowledgeApi } from "../services/knowledge.service";
import { ApiError } from "../lib/api";

test("knowledge requests reuse backend auth and preserve exact prefixes, keys and opaque cursors", async () => {
  const calls: { url: URL; init: RequestInit }[] = [];
  const api = createKnowledgeApi({ baseUrl: "https://backend.example/api", getToken: () => "synthetic-admin-token",
    randomUUID: () => "synthetic-correlation", fetchImpl: async (input, init = {}) => {
      calls.push({ url: new URL(String(input)), init });
      return new Response(JSON.stringify({ bucket: "knowledge-heritage", prefix: "Việt Nam/", folders: [], files: [], nextContinuationToken: null }));
    } });
  const controller = new AbortController();
  await api.list({ signal: controller.signal });
  assert.equal(calls[0].url.searchParams.has("prefix"), false);
  await api.list({ prefix: "Việt Nam/", continuationToken: "opaque+/=? token", limit: 7 });
  assert.equal(calls[1].url.searchParams.get("prefix"), "Việt Nam/");
  assert.equal(calls[1].url.searchParams.get("continuationToken"), "opaque+/=? token");
  await api.object("Việt Nam/read & notes.md", controller.signal);
  assert.equal(calls[2].url.searchParams.get("key"), "Việt Nam/read & notes.md");
  for (const { url, init } of calls) {
    assert.equal(url.origin, "https://backend.example");
    assert.equal(url.pathname.startsWith("/api/admin/knowledge/"), true);
    assert.equal(init.cache, "no-store");
    assert.equal(new Headers(init.headers).get("Authorization"), "Bearer synthetic-admin-token");
  }
  assert.equal(calls[0].init.signal, controller.signal);
});

test("knowledge write contracts use exact DTOs, no complete body and one DELETE key", async () => {
  const calls: { url: string; init: RequestInit }[] = [];
  const api = createKnowledgeApi({ getToken: () => "synthetic", randomUUID: () => "test",
    fetchImpl: async (url, init = {}) => { calls.push({ url: String(url), init });
      return init.method === "DELETE" ? new Response(null, { status: 204 }) : new Response("{}"); } });
  const upload = { folder: "area/", filename: "notes.md", contentType: "text/markdown", size: 12 };
  await api.beginUpload(upload);
  await api.complete("upload-id");
  await api.download("area/notes.md");
  await api.createFolder("area/", "child");
  await api.deleteObject("area/notes.md");
  assert.deepEqual(JSON.parse(String(calls[0].init.body)), upload);
  assert.equal(calls[1].init.body, undefined);
  assert.match(calls[1].url, /\/uploads\/upload-id\/complete$/);
  assert.deepEqual(JSON.parse(String(calls[2].init.body)), { key: "area/notes.md" });
  assert.deepEqual(JSON.parse(String(calls[3].init.body)), { parentPrefix: "area/", folderName: "child" });
  assert.deepEqual(JSON.parse(String(calls[4].init.body)), { key: "area/notes.md" });
  assert.equal(calls[4].init.method, "DELETE");
});

test("missing sessions do not make network calls and backend authorization errors remain distinguishable", async () => {
  const api = createKnowledgeApi({ getToken: () => null, fetchImpl: async () => { throw new Error("must not fetch"); } });
  await assert.rejects(api.list(), (e: unknown) => e instanceof ApiError && e.status === 401);
  for (const status of [401, 403, 404, 409, 410, 422, 503]) {
    const failing = createKnowledgeApi({ getToken: () => "synthetic", randomUUID: () => "test",
      fetchImpl: async () => new Response('{"detail":"safe backend error"}', { status }) });
    await assert.rejects(failing.list(), (e: unknown) => e instanceof ApiError && e.status === status);
  }
});
