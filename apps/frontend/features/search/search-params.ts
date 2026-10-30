import type { SearchState } from "./types";

export const SEARCH_PAGE_SIZE = 4;
export const UNCATEGORIZED = "Chưa phân loại";
export type SearchFilterKey = "regions" | "categories" | "locations";
const filterParams = { regions: "region", categories: "category", locations: "location" } as const;
const filterKeys = Object.keys(filterParams) as SearchFilterKey[];

function cleanValues(values: string[]) {
  return [...new Set(values.map((value) => value.trim().slice(0, 200)).filter(Boolean))].slice(0, 30);
}

export function readSearchState(params: URLSearchParams): SearchState {
  const rawPage = params.get("page") ?? "1";
  const page = /^\d+$/.test(rawPage) ? Number(rawPage) : 1;
  return {
    q: (params.get("q") ?? "").trim().slice(0, 200),
    regions: cleanValues(params.getAll("region")),
    categories: cleanValues(params.getAll("category")),
    locations: cleanValues(params.getAll("location")),
    page: Number.isSafeInteger(page) && page > 0 ? page : 1,
  };
}

/** Preserve unrelated URL parameters; changing a search constraint resets pagination. */
export function updateSearchParams(params: URLSearchParams, patch: Partial<SearchState>) {
  const next = new URLSearchParams(params);
  if (patch.q !== undefined) {
    const query = patch.q.trim().slice(0, 200);
    if (query) next.set("q", query);
    else next.delete("q");
  }
  for (const key of filterKeys) if (patch[key] !== undefined) {
    const param = filterParams[key];
    next.delete(param);
    for (const value of cleanValues(patch[key])) next.append(param, value);
  }
  const before = readSearchState(params);
  const after = readSearchState(next);
  const changesSearch = after.q !== before.q || filterKeys.some((key) => JSON.stringify(before[key]) !== JSON.stringify(after[key]));
  const page = patch.page ?? (changesSearch ? 1 : readSearchState(params).page);
  if (page > 1 && Number.isSafeInteger(page)) next.set("page", String(page));
  else next.delete("page");
  return next;
}

export function toggleSearchFilter(params: URLSearchParams, key: SearchFilterKey, value: string) {
  const selected = readSearchState(params)[key];
  return updateSearchParams(params, { [key]: selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value] });
}

export function searchHref(params: URLSearchParams, patch: Partial<SearchState> = {}) {
  const query = updateSearchParams(params, patch).toString();
  return `/search${query ? `?${query}` : ""}`;
}

export function normalizeSearchText(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d").replace(/Đ/g, "D").toLocaleLowerCase("vi");
}

/** A bounded page window, including the first/last page for very large collections. */
export function paginationPages(current: number, count: number): (number | "gap-left" | "gap-right")[] {
  const pages = new Set([1, count, current - 1, current, current + 1]);
  const sorted = [...pages].filter((page) => page >= 1 && page <= count).sort((a, b) => a - b);
  const result: (number | "gap-left" | "gap-right")[] = [];
  sorted.forEach((page, index) => {
    const distance = index > 0 ? page - sorted[index - 1] : 0;
    if (distance === 2) {
      result.push(page - 1);
    } else if (distance > 2) {
      result.push(page <= current ? "gap-left" : "gap-right");
    }
    result.push(page);
  });
  return result;
}
