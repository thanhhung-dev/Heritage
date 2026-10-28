/**
 * Normalize either a backend origin or an API base URL to the chat API.
 * Both http://localhost:8000 and http://localhost:8000/api are supported.
 */
export function chatApiUrl(apiUrl, path = "") {
  const base = apiUrl.trim().replace(/\/+$/, "");
  return `${base.endsWith("/api") ? base : `${base}/api`}/chat${path}`;
}

/**
 * Send the persisted-chat contract, with auth only when a token is supplied.
 *
 * @param {string} apiUrl
 * @param {string | import("../features/chat/types").ChatMessageRequest} payload
 * @param {{fetchImpl?: typeof fetch, randomUUID?: () => string, accessToken?: string | null, signal?: AbortSignal}} dependencies
 */
export function requestChat(apiUrl, payload, dependencies = {}) {
  const fetchImpl = dependencies.fetchImpl ?? fetch;
  const randomUUID = dependencies.randomUUID ?? (() => crypto.randomUUID());
  const request = typeof payload === "string" ? { message: payload } : payload;
  const body = { message: request.message, conversation_id: request.conversation_id ?? null };
  for (const key of ["heritage_context", "scene_context", "heritage_id"]) {
    if (request[key] !== undefined) body[key] = request[key];
  }

  return fetchImpl(chatApiUrl(apiUrl, "/message"), {
    method: "POST",
    signal: dependencies.signal,
    headers: {
      "Content-Type": "application/json",
      "X-Correlation-ID": randomUUID(),
      ...(dependencies.accessToken ? { Authorization: `Bearer ${dependencies.accessToken}` } : {}),
    },
    body: JSON.stringify(body),
  });
}
