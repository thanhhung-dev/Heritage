import assert from "node:assert/strict";
import test from "node:test";
import { createKnowledgeApi } from "../services/knowledge.service";
import { ApiError } from "../lib/api";

test("knowledge requests reuse backend auth and preserve exact prefixes, keys and opaque cursors", async () => {
  const calls: { url: URL; init: RequestInit }[] = [];
  const api = createKnowledgeApi({ baseUrl: "https://backend.example/api", getToken: () => "synthetic-admin-token",
    randomUUID: () => "synthetic-correlation", fetchImpl: async (input, init = {}) => {
      const url = new URL(String(input)); calls.push({ url, init });
      if (url.pathname.endsWith("/object")) return Response.json({ bucket: "knowledge-heritage", key: url.searchParams.get("key"),
        name: "read & notes.md", size: 1, lastModified: "2026-11-20T00:00:00Z", contentType: "text/markdown", etag: '"test"', metadata: {} });
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
    fetchImpl: async (url, init = {}) => {
      const path = new URL(String(url)).pathname; calls.push({ url: String(url), init });
      if (init.method === "DELETE") return new Response(null, { status: 204 });
      if (path.endsWith("/upload-url")) return Response.json({ uploadId: "upload-id", objectKey: "area/notes.md", method: "PUT",
        uploadUrl: "https://r2.example.invalid/staging", expiresIn: 300, sessionExpiresAt: "2099-01-01T00:00:00Z",
        requiredHeaders: { "Content-Type": "text/markdown", "If-None-Match": "*", "x-amz-meta-upload-id": "upload-id" } });
      if (path.endsWith("/complete")) return Response.json({ uploadId: "upload-id", status: "stored", object: {
        bucket: "knowledge-heritage", key: "area/notes.md", name: "notes.md", size: 12, lastModified: "2026-11-20T00:00:00Z",
        contentType: "text/markdown", etag: '"test"', metadata: {},
      } });
      if (path.endsWith("/download-url")) return Response.json({ key: "area/notes.md", downloadUrl: "https://r2.example.invalid/file", expiresIn: 300 });
      return Response.json({ name: "child", prefix: "area/child/" });
    } });
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

test("successful HTTP responses cannot substitute a different file or malformed signed upload contract", async () => {
  const object = { bucket: "knowledge-heritage", key: "area/notes.md", name: "notes.md", size: 12,
    lastModified: "2026-11-20T00:00:00Z", contentType: "text/markdown", etag: '"test"', metadata: {} };
  const ticket = { uploadId: "id", objectKey: "area/notes.md", method: "PUT", uploadUrl: "https://r2.example.invalid/private?signature=SYNTHETIC",
    expiresIn: 300, sessionExpiresAt: "2099-01-01T00:00:00Z",
    requiredHeaders: { "Content-Type": "text/markdown", "If-None-Match": "*", "x-amz-meta-upload-id": "id" } };
  const upload = { folder: "area/", filename: "notes.md", contentType: "text/markdown", size: 12 };
  function api(body: unknown) { return createKnowledgeApi({ getToken: () => "synthetic", randomUUID: () => "test", fetchImpl: async () => Response.json(body) }); }
  for (const value of [null, { ...object, key: "different.md" }, { ...object, bucket: "heritage" }, { ...object, size: -1 }]) {
    await assert.rejects(api(value).object("area/notes.md"), (error: unknown) => error instanceof ApiError && error.status === 503);
  }
  for (const value of [null, { ...ticket, objectKey: "different.md" }, { ...ticket, expiresIn: null },
      { ...ticket, requiredHeaders: { "If-None-Match": "*" } }, { ...ticket, requiredHeaders: { ...ticket.requiredHeaders, Authorization: "unsafe" } }]) {
    await assert.rejects(api(value).beginUpload(upload), (error: unknown) => error instanceof ApiError && error.status === 503 && !error.message.includes("SYNTHETIC"));
  }
  await assert.rejects(api({ key: "different.md", content: "x", size: 1, contentType: "text/plain; charset=utf-8", etag: '"test"' }).preview("area/notes.md"));
  await assert.rejects(api({ key: "area/notes.md", downloadUrl: "javascript:alert(1)", expiresIn: 300 }).download("area/notes.md"));
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
