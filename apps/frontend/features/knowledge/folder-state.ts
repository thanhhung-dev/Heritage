import { ApiError } from "../../lib/api";
import type { KnowledgeApi, KnowledgePage } from "./types";
import { isKnowledgeFile } from "./response-policy";

export function checkedPage(page: KnowledgePage): KnowledgePage {
  if (page?.bucket !== "knowledge-heritage" || typeof page.prefix !== "string"
      || (page.prefix !== "" && !page.prefix.endsWith("/"))
      || !Array.isArray(page.folders) || !page.folders.every(folder => folder && typeof folder.name === "string"
        && folder.name.length > 0 && folder.prefix === page.prefix + folder.name + "/" && !folder.name.includes("/"))
      || !Array.isArray(page.files) || !page.files.every(file => isKnowledgeFile(file)
        && file.key === page.prefix + file.name && !file.name.includes("/"))
      || !(page.nextContinuationToken === null || typeof page.nextContinuationToken === "string")) {
    throw new ApiError("The backend returned an unexpected knowledge listing.", 503);
  }
  return page;
}

export function appendKnowledgePage(current: KnowledgePage, next: KnowledgePage): KnowledgePage {
  checkedPage(next);
  if (current.prefix !== next.prefix) throw new ApiError("The folder changed during pagination. Refresh the listing.", 409);
  return { ...next,
    folders: Array.from(new Map([...current.folders, ...next.folders].map(folder => [folder.prefix, folder])).values()),
    files: Array.from(new Map([...current.files, ...next.files].map(file => [file.key, file])).values()),
  };
}

/** Filtering markers/staging can leave empty pages with a valid next token. */
export async function readKnowledgePage(api: KnowledgeApi, prefix?: string, cursor?: string, signal?: AbortSignal): Promise<KnowledgePage> {
  const seen = new Set<string>();
  if (cursor) seen.add(cursor);
  let page: KnowledgePage | null = null;
  while (true) {
    const next = checkedPage(await api.list({ prefix, continuationToken: cursor, signal }));
    if (prefix !== undefined && next.prefix !== prefix) {
      throw new ApiError("The backend returned a different folder. Refresh the listing.", 409);
    }
    page = page ? appendKnowledgePage(page, next) : next;
    if (next.nextContinuationToken !== null && seen.has(next.nextContinuationToken)) {
      throw new ApiError("Pagination did not advance. Refresh the listing.", 503);
    }
    if (next.files.length || next.folders.length || next.nextContinuationToken === null) return page;
    cursor = next.nextContinuationToken;
    seen.add(cursor);
  }
}

export function libraryHref(prefix?: string): string {
  return "/admin/documents" + (prefix === undefined ? "" : "?" + new URLSearchParams({ prefix }));
}

export function uploadHref(prefix?: string): string {
  return "/admin/documents/upload" + (prefix === undefined ? "" : "?" + new URLSearchParams({ prefix }));
}

export function documentHref(view: "details" | "metadata", key: string): string {
  return `/admin/documents/${view}?` + new URLSearchParams({ key });
}

export function breadcrumbParts(root: string, prefix: string): { label: string; prefix: string }[] {
  if (!prefix.startsWith(root)) return [];
  const relative = prefix.slice(root.length);
  let current = root;
  return relative.split("/").filter(Boolean).map(label => { current += label + "/"; return { label, prefix: current }; });
}
