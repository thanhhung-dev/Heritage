import { normalizeSearchText, UNCATEGORIZED } from "./search-params";
import type { HeritageSearchItem, SearchFacet, SearchLocationGroup } from "./types";

export const DESIGN_CATEGORIES = [
  "Imperial & Historic Relics",
  "Temples, Pagodas",
  "Natural Landscapes & Scenic Sites",
  "Traditional Craft Villages & Living Heritage",
  "Museums & Antiquities",
] as const;

export function searchImageUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  if (/^\/(?!\/)/.test(value) && !value.includes("\\")) return value;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}

export function heritageRegion(item: HeritageSearchItem): string {
  const region = item.region?.trim();
  if (!region) return "Other locations";
  const normalized = normalizeSearchText(region).replace(/\s+/g, "");
  if (normalized.includes("danang")) return "Đà Nẵng";
  if (normalized.includes("hue")) return "Huế";
  return region.split(",")[0].trim();
}

export function heritageLanguages(item: HeritageSearchItem): string[] {
  return [...new Set([item.language1?.name, item.language2?.name].filter((name): name is string => Boolean(name)))];
}

export function formatSearchDuration(seconds: number | null): string | null {
  return seconds && seconds > 0 ? `${Math.max(1, Math.round(seconds / 60))} min` : null;
}

export function catalogueFacets(items: HeritageSearchItem[]) {
  const categories = new Map<string, SearchFacet>(DESIGN_CATEGORIES.map((label) => [label, { value: label, label, count: 0 }]));
  const groups = new Map<string, SearchLocationGroup>();
  for (const item of items) {
    const category = item.category ?? UNCATEGORIZED;
    const facet = categories.get(category) ?? { value: category, label: category === UNCATEGORIZED ? "Uncategorized" : category, count: 0 };
    facet.count++;
    categories.set(category, facet);
    const region = heritageRegion(item);
    const group = groups.get(region) ?? { value: region, label: region, count: 0, sites: [] };
    group.count++;
    group.sites.push({ value: item.slug, label: item.title, count: 1 });
    groups.set(region, group);
  }
  return {
    categoryFacets: [...categories.values()],
    locationGroups: [...groups.values()].sort((a, b) => a.label.localeCompare(b.label, "vi")),
  };
}

/** Catalogue suggestions only; no fabricated tours or inferred personal preferences. */
export function catalogueRecommendations(items: HeritageSearchItem[], visible: HeritageSearchItem[], limit = 5): HeritageSearchItem[] {
  const shown = new Set(visible.map((item) => item.slug));
  const ordered = [...items.filter((item) => !shown.has(item.slug)), ...items.filter((item) => shown.has(item.slug))];
  return [...new Map(ordered.map((item) => [item.slug, item])).values()].slice(0, limit);
}
