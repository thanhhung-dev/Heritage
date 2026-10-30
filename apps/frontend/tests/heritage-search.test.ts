import assert from "node:assert/strict";
import test from "node:test";
import { readSearchState, searchHref, updateSearchParams, toggleSearchFilter, paginationPages, UNCATEGORIZED } from "../features/search/search-params";
import { searchHeritages, selectHeritages } from "../services/heritageSearchService";
import type { HeritageSearchItem, SearchState } from "../features/search/types";
import { catalogueFacets, catalogueRecommendations, heritageLanguages, searchImageUrl } from "../features/search/catalogue";

const state: SearchState = { q: "", regions: [], categories: [], locations: [], page: 1 };
const heritage: HeritageSearchItem = {
  id: 1, slug: "tu-duc-tomb", title: "Lăng Tự Đức", description: "Di sản Huế",
  tagline: null, region: "Huế, Việt Nam", category: "Di tích & kiến trúc",
  card_image_url: null, duration_seconds: 600,
};

test("search URL round-trips Unicode, filters and pagination without dropping unrelated parameters", () => {
  const original = new URLSearchParams("q=Lăng+Tự+Đức&region=Huế&category=Di+tích&page=3&source=library");
  const href = searchHref(original, { page: 2 });
  const restored = new URLSearchParams(href.split("?")[1]);
  assert.deepEqual(readSearchState(restored), { q: "Lăng Tự Đức", regions: ["Huế"], categories: ["Di tích"], locations: [], page: 2 });
  assert.equal(restored.get("source"), "library");
  assert.equal(original.get("page"), "3");
});

test("changing a search constraint resets the page and clearing filters removes their URL parameters", () => {
  const original = new URLSearchParams("q=Huế&region=Huế&category=Di+tích&page=4");
  assert.equal(updateSearchParams(original, { q: "Da Nang" }).get("page"), null);
  assert.equal(updateSearchParams(original, { regions: ["Đà Nẵng"] }).get("page"), null);
  assert.equal(updateSearchParams(original, { categories: ["Danh thắng"] }).get("page"), null);
  assert.equal(searchHref(original, { q: "", regions: [], categories: [], locations: [], page: 1 }), "/search");
});

test("malformed, negative and unsafe URL pages are normalized", () => {
  for (const page of ["-1", "0", "NaN", "2.4", "Infinity", "9007199254740992", "1e4"]) {
    assert.equal(readSearchState(new URLSearchParams({ page })).page, 1);
  }
});

test("accent-insensitive search combines all terms, region and explicit category", () => {
  const items = [heritage, { ...heritage, id: 2, slug: "marble-mountains", title: "Ngũ Hành Sơn", region: "Đà Nẵng", category: "Danh thắng" }];
  assert.equal(selectHeritages(items, { ...state, q: "LANG tu DUC", regions: ["hue"], categories: ["Di tích & kiến trúc"] }).total, 1);
  assert.equal(selectHeritages(items, { ...state, q: "ngu hanh", regions: ["da nang"], categories: ["Danh thắng"] }).items[0].slug, "marble-mountains");
  const empty = selectHeritages(items, { ...state, q: "không tồn tại" });
  assert.equal(empty.total, 0);
  assert.equal(empty.locationGroups.length, 2);
  assert.equal(empty.categoryFacets.filter((facet) => facet.count > 0).length, 2);
});

test("pagination has no overlaps and out-of-range requests resolve to the last valid page", () => {
  const items = Array.from({ length: 23 }, (_, id) => ({ ...heritage, id, slug: `heritage-${id}` }));
  const first = selectHeritages(items, state);
  const second = selectHeritages(items, { ...state, page: 2 });
  const last = selectHeritages(items, { ...state, page: 999 });
  assert.equal(first.items.length, 4);
  assert.equal(second.items.length, 4);
  assert.equal(last.items.length, 3);
  assert.equal(last.page, 6);
  const pages = Array.from({ length: last.page }, (_, index) => selectHeritages(items, { ...state, page: index + 1 }).items).flat();
  assert.equal(pages.length, 23);
  assert.equal(new Set(pages.map((item) => item.id)).size, 23);
  assert.deepEqual(paginationPages(50, 100), [1, "gap-left", 49, 50, 51, "gap-right", 100]);
  assert.deepEqual(paginationPages(1, 4), [1, 2, 3, 4]);
});

test("missing backend categories stay uncategorized rather than being guessed from titles", () => {
  const results = selectHeritages([{ ...heritage, category: null }], { ...state, categories: [UNCATEGORIZED] });
  assert.equal(results.total, 1);
  assert.equal(results.items[0].category, null);
  assert.equal(results.categoryFacets.find((facet) => facet.value === UNCATEGORIZED)?.count, 1);
});

test("the API adapter uses the existing list endpoint, accepts HeritageOut and forwards cancellation", async (context) => {
  const controller = new AbortController();
  const fetchMock = context.mock.method(globalThis, "fetch", async (url: string, options: RequestInit) => {
    assert.match(url, /\/api\/heritages$/);
    assert.equal(options.signal, controller.signal);
    assert.equal(options.cache, "no-store");
    return Response.json([{ id: 1, slug: "tu-duc-tomb", title: "Lăng Tự Đức", region: "Huế", publish_state: "published" }]);
  });
  try {
    const results = await searchHeritages(state, controller.signal);
    assert.equal(results.total, 1);
    assert.equal(results.items[0].category, null);
  } finally { fetchMock.mock.restore(); }
});

test("API errors and invalid payloads fail explicitly without silently substituting mock data", async (context) => {
  const fetchMock = context.mock.method(globalThis, "fetch", async () => new Response("unavailable", { status: 503 }));
  try {
    await assert.rejects(searchHeritages(state), /Không thể tải/);
    fetchMock.mock.mockImplementation(async () => Response.json({ items: [] }));
    await assert.rejects(searchHeritages(state));
  } finally { fetchMock.mock.restore(); }
});

test("catalogue metadata retains languages, headline and images while excluding unpublished tours", async (context) => {
  const fetchMock = context.mock.method(globalThis, "fetch", async () => Response.json([
    { ...heritage, headline: "A living story", language1: { code: "en", name: "English" }, language2: { code: "vi", name: "Vietnamese" }, publish_state: "published" },
    { ...heritage, id: 2, slug: "private-preview", publish_state: "preview" },
  ]));
  try {
    const results = await searchHeritages(state);
    assert.equal(results.total, 1);
    assert.equal(results.items[0].headline, "A living story");
    assert.deepEqual(heritageLanguages(results.items[0]), ["English", "Vietnamese"]);
    assert.equal(results.recommendations.length, 1);
  } finally { fetchMock.mock.restore(); }
});

test("sidebar counts use actual metadata and preserve the design categories without guessing", () => {
  const facets = catalogueFacets([heritage, { ...heritage, id: 2, slug: "other", region: "Da Nang City, Vietnam", category: null }]);
  assert.equal(facets.categoryFacets.find((facet) => facet.value === "Imperial & Historic Relics")?.count, 0);
  assert.equal(facets.categoryFacets.find((facet) => facet.value === UNCATEGORIZED)?.count, 1);
  assert.equal(facets.locationGroups.find((group) => group.value === "Đà Nẵng")?.sites[0].value, "other");
  assert.equal(facets.locationGroups.find((group) => group.value === "Huế")?.count, 1);
});

test("recommendations remain available for empty searches and never duplicate tours", () => {
  const items = Array.from({ length: 8 }, (_, id) => ({ ...heritage, id, slug: `tour-${id}` }));
  assert.equal(catalogueRecommendations(items, []).length, 5);
  const recommendations = catalogueRecommendations(items, items.slice(0, 2));
  assert.equal(recommendations[0].slug, "tour-2");
  assert.equal(new Set(recommendations.map((item) => item.slug)).size, 5);
  assert.equal(catalogueRecommendations([heritage, heritage], []).length, 1);
});

test("search imagery accepts API assets while rejecting unsafe URLs", () => {
  assert.equal(searchImageUrl("/images/heritage.jpg"), "/images/heritage.jpg");
  assert.equal(searchImageUrl("https://example.org/tour.webp"), "https://example.org/tour.webp");
  for (const url of ["javascript:alert(1)", "//other.example/image", "https://user:secret@example.org/image", "/\\evil.example/image"]) {
    assert.equal(searchImageUrl(url), null);
  }
});

test("checkbox URLs retain multiple selections, support legacy links and reset pagination on site changes", () => {
  let params = new URLSearchParams("region=Huế&category=Temples&page=3&source=library");
  params = toggleSearchFilter(params, "regions", "Đà Nẵng");
  params = toggleSearchFilter(params, "locations", "tu-duc-tomb");
  assert.deepEqual(readSearchState(params).regions, ["Huế", "Đà Nẵng"]);
  assert.deepEqual(readSearchState(params).locations, ["tu-duc-tomb"]);
  assert.equal(params.get("page"), null);
  assert.equal(params.get("source"), "library");
  params = toggleSearchFilter(params, "regions", "Huế");
  assert.deepEqual(params.getAll("region"), ["Đà Nẵng"]);
  const repeated = readSearchState(new URLSearchParams("region=Huế&region=Huế&region=&location=a&location=b"));
  assert.deepEqual(repeated.regions, ["Huế"]);
  assert.deepEqual(repeated.locations, ["a", "b"]);
});

test("selections use OR within each filter and AND across query, categories, regions and sites", () => {
  const items = [heritage, { ...heritage, id: 2, slug: "marble-mountains", title: "Ngũ Hành Sơn", region: "Da Nang City", category: "Natural Landscapes & Scenic Sites" }];
  const selection = { ...state, regions: ["Huế", "Đà Nẵng"], categories: ["Di tích & kiến trúc", "Natural Landscapes & Scenic Sites"] };
  assert.equal(selectHeritages(items, selection).total, 2);
  assert.equal(selectHeritages(items, { ...selection, locations: ["marble-mountains"] }).items[0].slug, "marble-mountains");
  const empty = selectHeritages(items, { ...selection, q: "missing site", locations: ["marble-mountains"] });
  assert.equal(empty.total, 0);
  assert.equal(empty.recommendations.length, 2);
  assert.equal(empty.locationGroups.length, 2);
});
