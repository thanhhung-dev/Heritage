import type { SearchState } from "./types";

export const SEARCH_PAGE_SIZE = 9;
export const UNCATEGORIZED = "Chưa phân loại";

export function readSearchState(params: URLSearchParams): SearchState {
  const rawPage = params.get("page") ?? "1";
  const page = /^\d+$/.test(rawPage) ? Number(rawPage) : 1;
  return {
    q: (params.get("q") ?? "").trim(),
    region: (params.get("region") ?? "").trim(),
    category: (params.get("category") ?? "").trim(),
    page: Number.isSafeInteger(page) && page > 0 ? page : 1,
  };
}

/** Preserve unrelated URL parameters; changing a search constraint resets pagination. */
export function updateSearchParams(params: URLSearchParams, patch: Partial<SearchState>) {
  const next = new URLSearchParams(params);
  for (const key of ["q", "region", "category"] as const) {
    if (patch[key] !== undefined) {
      const value = patch[key].trim();
      if (value) next.set(key, value);
      else next.delete(key);
    }
  }
  const changesSearch = ["q", "region", "category"].some(
    (key) => key in patch && next.get(key) !== params.get(key),
  );
  const page = patch.page ?? (changesSearch ? 1 : readSearchState(params).page);
  if (page > 1 && Number.isSafeInteger(page)) next.set("page", String(page));
  else next.delete("page");
  return next;
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
