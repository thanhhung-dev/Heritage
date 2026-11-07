import { buildApiUrl, apiFetch, type ApiDependencies } from "./api";

export type ChatRequestDependencies = ApiDependencies;
export { buildApiUrl as chatApiUrl };

/**
 * Send a chat request with a bounded, browser-generated correlation ID.
 */
export function requestChat(
  apiUrl: string,
  message: string,
  dependencies: ChatRequestDependencies = {},
): Promise<Response> {
  return apiFetch(
    "/chat",
    {
      method: "POST",
      body: JSON.stringify({ message, use_rag: true }),
    },
    dependencies,
    apiUrl,
  );
}
