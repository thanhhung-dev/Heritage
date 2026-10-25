import assert from "node:assert/strict";
import test from "node:test";
import { readSearchState, searchHref, updateSearchParams, paginationPages, UNCATEGORIZED } from "../features/search/search-params";
import { searchHeritages, selectHeritages } from "../services/heritageSearchService";
import type { HeritageSearchItem, SearchState } from "../features/search/types";

const state: SearchState = { q: "", region: "", category: "", page: 1 };
const heritage: HeritageSearchItem = {
  id: 1, slug: "tu-duc-tomb", title: "Lăng Tự Đức", description: "Di sản Huế",
  tagline: null, region: "Huế, Việt Nam", category: "Di tích & kiến trúc",
  card_image_url: null, duration_seconds: 600,
};

test("search URL round-trips Unicode, filters and pagination without dropping unrelated parameters", () => {
  const original = new URLSearchParams("q=Lăng+Tự+Đức&region=Huế&category=Di+tích&page=3&source=library");
  const href = searchHref(original, { page: 2 });
  const restored = new URLSearchParams(href.split("?")[1]);
  assert.deepEqual(readSearchState(restored), { q: "Lăng Tự Đức", region: "Huế", category: "Di tích", page: 2 });
  assert.equal(restored.get("source"), "library");
  assert.equal(original.get("page"), "3");
});

test("changing a search constraint resets the page and clearing filters removes their URL parameters", () => {
  const original = new URLSearchParams("q=Huế&region=Huế&category=Di+tích&page=4");
  assert.equal(updateSearchParams(original, { q: "Da Nang" }).get("page"), null);
  assert.equal(updateSearchParams(original, { region: "Đà Nẵng" }).get("page"), null);
  assert.equal(updateSearchParams(original, { category: "Danh thắng" }).get("page"), null);
  assert.equal(searchHref(original, { q: "", region: "", category: "", page: 1 }), "/search");
});

test("malformed, negative and unsafe URL pages are normalized", () => {
  for (const page of ["-1", "0", "NaN", "2.4", "Infinity", "9007199254740992", "1e4"]) {
    assert.equal(readSearchState(new URLSearchParams({ page })).page, 1);
  }
});

test("accent-insensitive search combines all terms, region and explicit category", () => {
  const items = [heritage, { ...heritage, id: 2, slug: "marble-mountains", title: "Ngũ Hành Sơn", region: "Đà Nẵng", category: "Danh thắng" }];
  assert.equal(selectHeritages(items, { ...state, q: "LANG tu DUC", region: "hue", category: "Di tích & kiến trúc" }).total, 1);
  assert.equal(selectHeritages(items, { ...state, q: "ngu hanh", region: "da nang", category: "Danh thắng" }).items[0].slug, "marble-mountains");
  const empty = selectHeritages(items, { ...state, q: "không tồn tại" });
  assert.equal(empty.total, 0);
  assert.equal(empty.regions.length, 2);
  assert.equal(empty.categories.length, 2);
});

test("pagination has no overlaps and out-of-range requests resolve to the last valid page", () => {
  const items = Array.from({ length: 23 }, (_, id) => ({ ...heritage, id, slug: `heritage-${id}` }));
  const first = selectHeritages(items, state);
  const second = selectHeritages(items, { ...state, page: 2 });
  const last = selectHeritages(items, { ...state, page: 999 });
  assert.equal(first.items.length, 9);
  assert.equal(second.items.length, 9);
  assert.equal(last.items.length, 5);
  assert.equal(last.page, 3);
  assert.equal(new Set([...first.items, ...second.items, ...last.items].map((item) => item.id)).size, 23);
  assert.deepEqual(paginationPages(50, 100), [1, "gap-left", 49, 50, 51, "gap-right", 100]);
  assert.deepEqual(paginationPages(1, 4), [1, 2, 3, 4]);
});

test("missing backend categories stay uncategorized rather than being guessed from titles", () => {
  const results = selectHeritages([{ ...heritage, category: null }], { ...state, category: UNCATEGORIZED });
  assert.equal(results.total, 1);
  assert.equal(results.items[0].category, null);
  assert.deepEqual(results.categories, [UNCATEGORIZED]);
});

test("the API adapter uses the existing list endpoint, accepts HeritageOut and forwards cancellation", async (context) => {
  const controller = new AbortController();
  const fetchMock = context.mock.method(globalThis, "fetch", async (url: string, options: RequestInit) => {
    assert.match(url, /\/api\/heritages$/);
    assert.equal(options.signal, controller.signal);
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
