import assert from "node:assert/strict";
import test from "node:test";

import { appendCatalogPage, toCatalogCard } from "../features/home/catalog-cards";
import { getCatalogDetail, getCatalogSection, getCatalogSections, type CatalogContent } from "../services/catalog.service";

const artifact: CatalogContent = {
  id: 10, slug: "fixture-object", title: "Fixture object", description: "Verified fixture description",
  region: null, entity_type: "artifact", categories: ["artifact"], primary_category: "artifact",
  card_image_url: "https://example.org/object.jpg", source_url: "https://example.org/source",
  metadata: {}, heritage_id: null, heritage_slug: null, href: "/catalog/fixture-object",
};

test("catalog cards keep entity identity and do not invent dates, languages or place links", () => {
  const card = toCatalogCard(artifact);
  assert.equal(card.title, artifact.title);
  assert.equal(card.href, "/catalog/fixture-object");
  assert.equal(card.published, null);
  assert.equal(card.language_label, "");
  assert.equal(card.region, null);
  const place = toCatalogCard({ ...artifact, entity_type: "place", heritage_slug: "source-place", href: "/content/source-place" });
  assert.equal(place.href, "/content/source-place");
});

test("verified artifact period is displayed only when explicitly supplied", () => {
  const card = toCatalogCard({ ...artifact, metadata: { period: { value: "Source-provided period", source_url: "https://example.org/period" } } });
  assert.equal(card.published, "Source-provided period");
});

test("pagination deduplicates entity IDs and preserves the backend next page", () => {
  const next = { ...artifact, id: 11, slug: "another-object" };
  const merged = appendCatalogPage({ items: [artifact], next_offset: 8 }, { items: [artifact, next], next_offset: 16 });
  assert.deepEqual(merged.items.map((item) => item.id), [10, 11]);
  assert.equal(merged.next_offset, 16);
});

test("all catalog requests bypass caches and preserve abort signals and entity detail slugs", async (t) => {
  const requests: { url: string; options?: RequestInit }[] = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    requests.push({ url: String(url), options });
    return new Response(JSON.stringify({ items: [], next_offset: null }), { status: 200 });
  };
  t.after(() => { globalThis.fetch = original; });
  const controller = new AbortController();
  await getCatalogSections(controller.signal);
  await getCatalogSection("artifact_collection", 8);
  await getCatalogDetail("an object/01", controller.signal);
  assert.ok(requests.every((request) => request.options?.cache === "no-store"));
  assert.equal(requests[0].options?.signal, controller.signal);
  assert.ok(requests[1].url.endsWith("/catalog/sections/artifact_collection?limit=8&offset=8"));
  assert.ok(requests[2].url.endsWith("/catalog/contents/an%20object%2F01"));
});
