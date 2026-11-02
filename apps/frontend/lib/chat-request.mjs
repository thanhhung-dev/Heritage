/**
 * Send a chat request with a bounded, browser-generated correlation ID.
 * Dependencies are injectable so this transport contract can be tested in Node.
 *
 * @param {string} apiUrl
 * @param {string} message
 * @param {{fetchImpl?: typeof fetch, randomUUID?: () => string}} dependencies
 */
export function requestChat(apiUrl, message, dependencies = {}) {
  const fetchImpl = dependencies.fetchImpl ?? fetch;
  const randomUUID = dependencies.randomUUID ?? (() => crypto.randomUUID());

  return fetchImpl(chatApiUrl(apiUrl, "/chat"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Correlation-ID": randomUUID(),
    },
    body: JSON.stringify({ message, use_rag: true }),
  });
}

/**
 * Join an API base URL to a chat route without duplicating `/api` when the
 * configured URL already ends with that prefix.
 *
 * @param {string} apiUrl
 * @param {string} route
 */
export function chatApiUrl(apiUrl, route) {
  const base = apiUrl.replace(/\/+$/, "");
  const apiRoot = /\/api$/i.test(base) ? base : `${base}/api`;
  const normalizedRoute = route.startsWith("/") ? route : `/${route}`;

  return `${apiRoot}${normalizedRoute}`;
}
