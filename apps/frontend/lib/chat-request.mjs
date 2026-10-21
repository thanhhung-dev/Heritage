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

  return fetchImpl(`${apiUrl}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Correlation-ID": randomUUID(),
    },
    body: JSON.stringify({ message, use_rag: true }),
  });
}
