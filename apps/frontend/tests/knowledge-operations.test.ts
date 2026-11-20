import assert from "node:assert/strict";
import test from "node:test";
import { createKnowledgeApi, knowledgeError } from "../services/knowledge.service";
import { ApiError } from "../lib/api";
import { checkedPage, uploadHref, libraryHref, documentHref } from "../features/knowledge/folder-state";
import { formatFileSize } from "../features/knowledge/file-policy";
import { formatEntryProgress, uploadPercent, uploadStateLabel } from "../features/knowledge/UploadControls";
import type { UploadEntry } from "../features/knowledge/upload-queue";

test("document operations handle preview 413/404, download URL requests, folder creation and exact-key deletion", async () => {
  const seen: { method: string; url: string; body?: string }[] = [];
  const api = createKnowledgeApi({
    baseUrl: "https://backend.example/api",
    getToken: () => "admin-jwt",
    randomUUID: () => "req-1",
    fetchImpl: async (input, init = {}) => {
      const url = String(input);
      seen.push({ method: init.method ?? "GET", url, body: init.body ? String(init.body) : undefined });
      if (url.includes("oversized.md")) {
        return new Response(JSON.stringify({ detail: "File exceeds preview size limit" }), { status: 413 });
      }
      if (url.includes("missing.md")) {
        return new Response(JSON.stringify({ detail: "Object not found" }), { status: 404 });
      }
      if (url.includes("/preview?")) {
        return Response.json({
          key: "docs/safe.md",
          content: "<script>alert(1)</script>\n# Heading",
          contentType: "text/plain; charset=utf-8",
          size: 35,
          etag: '"etag-1"',
        });
      }
      if (url.endsWith("/download-url")) {
        return Response.json({
          key: "docs/safe.md",
          downloadUrl: "https://r2.example.invalid/download-signed",
          expiresIn: 120,
        });
      }
      if (url.endsWith("/folders")) {
        return Response.json({ name: "archives", prefix: "docs/archives/" });
      }
      if (url.endsWith("/objects") && init.method === "DELETE") {
        return new Response(null, { status: 204 });
      }
      return Response.json({});
    },
  });

  await assert.rejects(api.preview("docs/oversized.md"), (e: unknown) => e instanceof ApiError && e.status === 413);
  await assert.rejects(api.preview("docs/missing.md"), (e: unknown) => e instanceof ApiError && e.status === 404);

  const preview = await api.preview("docs/safe.md");
  assert.equal(preview.content, "<script>alert(1)</script>\n# Heading");

  const download = await api.download("docs/safe.md");
  assert.equal(download.downloadUrl, "https://r2.example.invalid/download-signed");

  const folder = await api.createFolder("docs/", "archives");
  assert.equal(folder.prefix, "docs/archives/");

  await api.deleteObject("docs/safe.md");
  const delCall = seen.find(c => c.method === "DELETE");
  assert.ok(delCall);
  assert.deepEqual(JSON.parse(delCall.body ?? "{}"), { key: "docs/safe.md" });
});

test("upload progress formatting and state labels keep 100% transfer distinct from Stored in R2", () => {
  const uploadingEntry: UploadEntry = {
    id: "u-1",
    file: new File(["hello"], "note.md"),
    folder: "docs/",
    contentType: "text/markdown",
    state: "uploading",
    loaded: 5,
    total: 5,
  };
  assert.equal(uploadPercent(uploadingEntry), 99);
  assert.equal(uploadStateLabel("uploading"), "Uploading");
  assert.equal(uploadStateLabel("verifying"), "Verifying upload");
  assert.equal(uploadStateLabel("stored"), "Stored in R2");
  assert.match(formatEntryProgress(uploadingEntry), /99%/);

  const storedEntry: UploadEntry = { ...uploadingEntry, state: "stored" };
  assert.equal(uploadPercent(storedEntry), 100);
  assert.equal(formatFileSize(1536), "1.5 KiB");
});

test("checkedPage rejects wrong bucket and route builders preserve exact prefixes and keys", () => {
  assert.throws(
    () =>
      checkedPage({
        bucket: "heritage" as "knowledge-heritage",
        prefix: "",
        folders: [],
        files: [],
        nextContinuationToken: null,
      }),
    /unexpected knowledge listing/,
  );
  assert.equal(uploadHref("Việt Nam/"), "/admin/documents/upload?prefix=Vi%E1%BB%87t+Nam%2F");
  assert.equal(libraryHref("Việt Nam/"), "/admin/documents?prefix=Vi%E1%BB%87t+Nam%2F");
  assert.equal(documentHref("metadata", "Việt Nam/note.md"), "/admin/documents/metadata?key=Vi%E1%BB%87t+Nam%2Fnote.md");
  assert.match(knowledgeError(new ApiError("Unauthorized", 401)), /session expired/i);
  assert.match(knowledgeError(new ApiError("Forbidden", 403)), /permission/i);
  assert.match(knowledgeError(new ApiError("Expired", 410)), /upload session expired/i);
  assert.match(knowledgeError(new ApiError("Invalid", 422)), /rejected/i);
});
