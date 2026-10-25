import { z } from "zod";
import { API_BASE_URL } from "../config/api";
import { normalizeSearchText, SEARCH_PAGE_SIZE, UNCATEGORIZED } from "../features/search/search-params";
import type { HeritageSearchItem, SearchResults, SearchState } from "../features/search/types";

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
});

export function selectHeritages(items: HeritageSearchItem[], state: SearchState): SearchResults {
  const terms = normalizeSearchText(state.q).split(/\s+/).filter(Boolean);
  const region = normalizeSearchText(state.region);
  const category = normalizeSearchText(state.category);
  const filtered = items.filter((item) => {
    const text = normalizeSearchText([item.title, item.tagline, item.description, item.region, item.category].filter(Boolean).join(" "));
    return terms.every((term) => text.includes(term))
      && (!region || normalizeSearchText(item.region ?? "").includes(region))
      && (!category || normalizeSearchText(item.category ?? UNCATEGORIZED) === category);
  });
  const pageCount = Math.max(1, Math.ceil(filtered.length / SEARCH_PAGE_SIZE));
  const page = Math.min(state.page, pageCount);
  return {
    items: filtered.slice((page - 1) * SEARCH_PAGE_SIZE, page * SEARCH_PAGE_SIZE),
    total: filtered.length,
    page,
    pageCount,
    pageSize: SEARCH_PAGE_SIZE,
    // Facets come from the whole catalogue, so empty results never erase the filters.
    regions: [...new Set(items.flatMap((item) => item.region ? [item.region] : []))].sort((a, b) => a.localeCompare(b, "vi")),
    categories: [...new Set(items.map((item) => item.category ?? UNCATEGORIZED))].sort((a, b) => a.localeCompare(b, "vi")),
  };
}

export async function searchHeritages(state: SearchState, signal?: AbortSignal): Promise<SearchResults> {
  // FastAPI currently exposes a published list, without search/pagination parameters.
  // Keep this adapter replaceable when the backend introduces a paginated search contract.
  const response = await fetch(`${API_BASE_URL.replace(/\/$/, "")}/heritages`, {
    signal,
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error("Không thể tải danh sách di sản.");
  const items = z.array(heritageSchema).parse(await response.json());
  return selectHeritages(items, state);
}
