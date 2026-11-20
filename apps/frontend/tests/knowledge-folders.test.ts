import assert from "node:assert/strict";
import test from "node:test";
import { appendKnowledgePage, breadcrumbParts, documentHref, libraryHref, readKnowledgePage } from "../features/knowledge/folder-state";
import { createKnowledgeApi } from "../services/knowledge.service";
import type { KnowledgePage } from "../features/knowledge/types";

const empty: KnowledgePage = { bucket: "knowledge-heritage", prefix: "scope/", files: [], folders: [], nextContinuationToken: null };
test("empty filtered pages continue until data or null and never repeat the same opaque token", async () => {
  const cursors: (string | null)[] = [];
  const api = createKnowledgeApi({ getToken: () => "synthetic", randomUUID: () => "test", fetchImpl: async url => {
    const cursor = new URL(String(url)).searchParams.get("continuationToken"); cursors.push(cursor);
    return Response.json(cursor ? { ...empty, files: [{ name: "x.md", key: "scope/x.md", size: 1, lastModified: "2026-11-20T00:00:00Z" }] }
      : { ...empty, nextContinuationToken: "opaque+/token" });
  } });
  const page = await readKnowledgePage(api);
  assert.equal(page.files.length, 1); assert.deepEqual(cursors, [null, "opaque+/token"]);
  const repeating = createKnowledgeApi({ getToken: () => "synthetic", randomUUID: () => "test",
    fetchImpl: async () => Response.json({ ...empty, nextContinuationToken: "same" }) });
  await assert.rejects(readKnowledgePage(repeating), /Pagination did not advance/);
});

test("folder pagination deduplicates exact identity and cannot mix prefixes", () => {
  const page = { ...empty, folders: [{ name: "Việt Nam", prefix: "scope/Việt Nam/" }] };
  const merged = appendKnowledgePage(page, { ...page, nextContinuationToken: "next" });
  assert.equal(merged.folders.length, 1); assert.equal(merged.nextContinuationToken, "next");
  assert.throws(() => appendKnowledgePage(page, { ...page, prefix: "other/" }));
});

test("breadcrumbs, browser URLs and details retain exact scope and Unicode keys", () => {
  assert.deepEqual(breadcrumbParts("scope/", "scope/Việt Nam/history/"), [
    { label: "Việt Nam", prefix: "scope/Việt Nam/" }, { label: "history", prefix: "scope/Việt Nam/history/" }]);
  assert.deepEqual(breadcrumbParts("scope/", "other/"), []);
  assert.equal(libraryHref(), "/admin/documents");
  assert.equal(new URL(libraryHref("scope/Việt Nam/"), "https://frontend.test").searchParams.get("prefix"), "scope/Việt Nam/");
  const key = "scope/read & notes.md";
  assert.equal(new URL(documentHref("details", key), "https://frontend.test").searchParams.get("key"), key);
});
