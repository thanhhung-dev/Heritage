import { apiFetch, ApiError, parseApiResponse, type ApiDependencies } from "../lib/api";
import { getAccessToken } from "../lib/auth";
import { checkedCompletion, checkedDownload, checkedFolder, checkedObject, checkedPreview, checkedTicket } from "../features/knowledge/response-policy";
import type { KnowledgeApi, KnowledgeCompletion, KnowledgeDownload, KnowledgeFolder,
  KnowledgeObject, KnowledgePage, KnowledgePreview, KnowledgeUploadTicket } from "../features/knowledge/types";

interface KnowledgeDependencies extends Omit<ApiDependencies, "accessToken" | "signal"> {
  getToken?: () => string | null;
  baseUrl?: string;
}

/** Same-origin API client only. R2 transfers must never use this auth wrapper. */
export function createKnowledgeApi(deps: KnowledgeDependencies = {}): KnowledgeApi {
  const prefix = "/admin/knowledge";
  async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const accessToken = (deps.getToken ?? getAccessToken)();
    if (!accessToken) throw new ApiError("Sign in with an administrator account to continue.", 401);
    const response = await apiFetch(prefix + path, { cache: "no-store", ...options },
      { fetchImpl: deps.fetchImpl, randomUUID: deps.randomUUID, accessToken }, deps.baseUrl);
    return parseApiResponse<T>(response);
  }
  function post<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
    return request<T>(path, { method: "POST", signal, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
  }
  function query(key: string) { return new URLSearchParams({ key }).toString(); }
  return {
    list({ prefix: folder, continuationToken, limit = 100, signal } = {}) {
      const params = new URLSearchParams({ limit: String(limit) });
      if (folder !== undefined) params.set("prefix", folder);
      if (continuationToken !== undefined) params.set("continuationToken", continuationToken);
      return request<KnowledgePage>(`/objects?${params}`, { signal });
    },
    object: async (key, signal) => checkedObject(await request<KnowledgeObject>(`/object?${query(key)}`, { signal }), key),
    preview: async (key, signal) => checkedPreview(await request<KnowledgePreview>(`/preview?${query(key)}`, { signal }), key),
    beginUpload: async (data, signal) => checkedTicket(await post<KnowledgeUploadTicket>("/upload-url", data, signal), data),
    complete: async (uploadId, signal) => checkedCompletion(await post<KnowledgeCompletion>(`/uploads/${encodeURIComponent(uploadId)}/complete`, undefined, signal), uploadId),
    download: async (key, signal) => checkedDownload(await post<KnowledgeDownload>("/download-url", { key }, signal), key),
    createFolder: async (parentPrefix, folderName, signal) => checkedFolder(await post<KnowledgeFolder>("/folders", { parentPrefix, folderName }, signal), parentPrefix, folderName),
    async deleteObject(key, signal) {
      await request<void>("/objects", { method: "DELETE", body: JSON.stringify({ key }), signal });
    },
  };
}

export const knowledgeApi = createKnowledgeApi();

export function knowledgeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "Your session expired or is unavailable. Sign in with an administrator account.";
    if (error.status === 403) return "You do not have permission to perform this action.";
    if (error.status === 410) return "This upload session expired. Retry to request a new session.";
    if (error.status === 422) return "The filename, path, file type, size or file content was rejected. Check the selected file.";
    return error.message;
  }
  return "The request could not be completed. Check your connection and try again.";
}

export function isAborted(error: unknown): boolean {
  return error instanceof Error && error.name === "AbortError";
}
