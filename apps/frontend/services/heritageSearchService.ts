import { z } from "zod";
import { API_BASE_URL } from "../config/api";
import { normalizeSearchText, SEARCH_PAGE_SIZE, UNCATEGORIZED } from "../features/search/search-params";
import type { HeritageSearchItem, SearchResults, SearchState } from "../features/search/types";
import { catalogueFacets, catalogueRecommendations, heritageRegion, searchImageUrl } from "../features/search/catalogue";
import { heritageCategory } from "../features/search/heritage-taxonomy";

const nullableText = z.string().nullish().transform((value) => value?.trim() || null);
const heritageSchema = z.object({
  id: z.number(),
  slug: z.string().min(1),
  title: z.string().min(1),
  description: nullableText,
  tagline: nullableText,
  region: nullableText,
  // Prefer API metadata, then the explicitly authored catalogue taxonomy.
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
  const heroImages = [...new Set(items.flatMap((item) => [
    searchImageUrl(item.splash_image_url), searchImageUrl(item.card_image_url),
  ]).filter((image): image is string => Boolean(image)))].slice(0, 4);
  return {
    items: visible,
    total: filtered.length,
    page,
    pageCount,
    pageSize: SEARCH_PAGE_SIZE,
    // Facets come from the whole catalogue, so empty results never erase the filters.
    ...catalogueFacets(items),
    recommendations: catalogueRecommendations(items, visible),
    heroImage: heroImages[0] ?? null,
    heroFallbackImages: heroImages.slice(1),
  };
}

export async function searchHeritages(state: SearchState, signal?: AbortSignal): Promise<SearchResults> {
  return selectHeritages(await fetchHeritageCatalogue(signal), state);
}

export async function fetchHeritageCatalogue(signal?: AbortSignal): Promise<HeritageSearchItem[]> {
  // FastAPI currently exposes a published list, without search/pagination parameters.
  // Keep this adapter replaceable when the backend introduces a paginated search contract.
  const response = await fetch(heritageCatalogueEndpoint(API_BASE_URL), {
    signal,
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error("Không thể tải danh sách di sản.");
  const parsed = z.array(heritageSchema).parse(await response.json());
  const seenSlugs = new Set<string>();
  const seenIds = new Set<number>();
  return parsed.filter((item) => {
    if (item.publish_state !== undefined && item.publish_state !== "published") return false;
    if (seenSlugs.has(item.slug) || seenIds.has(item.id)) return false;
    seenSlugs.add(item.slug); seenIds.add(item.id);
    return true;
  }).map((item) => ({
    ...item,
    category: heritageCategory(item.slug, item.category),
    card_image_url: searchImageUrl(item.card_image_url),
    splash_image_url: searchImageUrl(item.splash_image_url),
  }));
}

/** Accept the project's API origin, /api base or same-origin proxy configuration. */
export function heritageCatalogueEndpoint(base: string): string {
  const normalized = base.trim().replace(/\/+$/, "");
  return `${normalized.endsWith("/api") ? normalized : `${normalized}/api`}/heritages`;
}
