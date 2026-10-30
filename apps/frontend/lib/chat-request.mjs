/**
 * Send a chat request with a bounded, browser-generated correlation ID.
 * Dependencies are injectable so this transport contract can be tested in Node.
 *
 * @param {string} apiUrl
 * @param {string} message
 * @param {{fetchImpl?: typeof fetch, randomUUID?: () => string, accessToken?: string | null, signal?: AbortSignal}} dependencies
 */
export function requestChat(apiUrl, message, dependencies = {}) {
  const fetchImpl = dependencies.fetchImpl ?? fetch;
  const randomUUID = dependencies.randomUUID ?? (() => crypto.randomUUID());
  const base = apiUrl.trim().replace(/\/+$/, "");
  const url = `${base.endsWith("/api") ? base : `${base}/api`}/chat`;

  return fetchImpl(url, {
    method: "POST",
    signal: dependencies.signal,
    headers: {
      "Content-Type": "application/json",
      "X-Correlation-ID": randomUUID(),
      ...(dependencies.accessToken ? { Authorization: `Bearer ${dependencies.accessToken}` } : {}),
    },
    body: JSON.stringify({ message, use_rag: true }),
  });
}
