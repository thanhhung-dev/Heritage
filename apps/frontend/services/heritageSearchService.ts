import { z } from "zod";
import { API_BASE_URL } from "../config/api";
import { normalizeSearchText, SEARCH_PAGE_SIZE, UNCATEGORIZED } from "../features/search/search-params";
import type { HeritageSearchItem, SearchResults, SearchState } from "../features/search/types";
import { catalogueFacets, catalogueRecommendations, heritageRegion, searchImageUrl } from "../features/search/catalogue";

const nullableText = z.string().nullish().transform((value) => value?.trim() || null);
const heritageSchema = z.object({
  id: z.number(),
  slug: z.string().min(1),
  title: z.string().min(1),
  description: nullableText,
  tagline: nullableText,
  region: nullableText,
  // The current HeritageOut has no category field. Never guess it from a title.
  category: nullableText,
  card_image_url: nullableText,
  duration_seconds: z.number().nonnegative().nullish().transform((value) => value ?? null),
  headline: nullableText,
  splash_image_url: nullableText,
  language1: z.object({ code: z.string(), name: z.string() }).nullish().transform((value) => value ?? null),
  language2: z.object({ code: z.string(), name: z.string() }).nullish().transform((value) => value ?? null),
  publish_state: z.string().optional(),
});

export function selectHeritages(items: HeritageSearchItem[], state: SearchState): SearchResults {
  const terms = normalizeSearchText(state.q).split(/\s+/).filter(Boolean);
  const regions = state.regions.map(normalizeSearchText);
  const categories = state.categories.map(normalizeSearchText);
  const filtered = items.filter((item) => {
    const text = normalizeSearchText([item.title, item.headline, item.tagline, item.description, item.region, item.category].filter(Boolean).join(" "));
    return terms.every((term) => text.includes(term))
      && (!regions.length || regions.some((region) => normalizeSearchText(item.region ?? "").includes(region) || normalizeSearchText(heritageRegion(item)).includes(region)))
      && (!categories.length || categories.includes(normalizeSearchText(item.category ?? UNCATEGORIZED)))
      && (!state.locations.length || state.locations.includes(item.slug));
  });
  const pageCount = Math.max(1, Math.ceil(filtered.length / SEARCH_PAGE_SIZE));
  const page = Math.min(state.page, pageCount);
  const visible = filtered.slice((page - 1) * SEARCH_PAGE_SIZE, page * SEARCH_PAGE_SIZE);
  return {
    items: visible,
    total: filtered.length,
    page,
    pageCount,
    pageSize: SEARCH_PAGE_SIZE,
    // Facets come from the whole catalogue, so empty results never erase the filters.
    ...catalogueFacets(items),
    recommendations: catalogueRecommendations(items, visible),
    heroImage: items.map((item) => searchImageUrl(item.splash_image_url) ?? searchImageUrl(item.card_image_url)).find(Boolean) ?? null,
  };
}

export async function searchHeritages(state: SearchState, signal?: AbortSignal): Promise<SearchResults> {
  return selectHeritages(await fetchHeritageCatalogue(signal), state);
}

export async function fetchHeritageCatalogue(signal?: AbortSignal): Promise<HeritageSearchItem[]> {
  // FastAPI currently exposes a published list, without search/pagination parameters.
  // Keep this adapter replaceable when the backend introduces a paginated search contract.
  const response = await fetch(`${API_BASE_URL.replace(/\/$/, "")}/heritages`, {
    signal,
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error("Không thể tải danh sách di sản.");
  return z.array(heritageSchema).parse(await response.json())
    .filter((item) => item.publish_state === undefined || item.publish_state === "published");
}
