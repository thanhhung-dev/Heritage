import { chatApiUrl } from "./chat-request.mjs";

/**
 * Build the bounded guest history accepted by the persisted chat endpoint.
 * Authenticated conversations use their server-side history instead.
 *
 * @param {Array<{role: "user" | "assistant", content: string}>} messages
 * @returns {Array<{role: "user" | "assistant", content: string}>}
 */
export function createConversationContext(messages) {
  const recentMessages = messages
    .filter(
      (message) =>
        (message.role === "user" || message.role === "assistant") &&
        typeof message.content === "string" &&
        message.content.trim().length > 0,
    )
    .slice(-6);

  let totalCharacters = 0;
  const boundedMessages = [];

  for (const message of [...recentMessages].reverse()) {
    const remainingCharacters = 6000 - totalCharacters;
    if (remainingCharacters <= 0) break;

    const content = message.content.trim().slice(0, Math.min(2000, remainingCharacters));
    if (!content) continue;

    boundedMessages.push({ role: message.role, content });
    totalCharacters += content.length;
  }

  return boundedMessages.reverse();
}

/**
 * Send a tour-scoped chat request using the structured conversation API.
 *
 * @param {string} apiUrl
 * @param {object} request
 * @param {{fetchImpl?: typeof fetch, randomUUID?: () => string, accessToken?: string | null, signal?: AbortSignal}} dependencies
 */
export function requestSceneChat(apiUrl, request, dependencies = {}) {
  const fetchImpl = dependencies.fetchImpl ?? fetch;
  const randomUUID = dependencies.randomUUID ?? (() => crypto.randomUUID());
  /** @type {Record<string, string>} */
  const headers = {
    "Content-Type": "application/json",
    "X-Correlation-ID": randomUUID(),
  };

  if (dependencies.accessToken) {
    headers.Authorization = `Bearer ${dependencies.accessToken}`;
  }

  return fetchImpl(chatApiUrl(apiUrl, "/chat/message"), {
    method: "POST",
    headers,
    body: JSON.stringify(request),
    signal: dependencies.signal,
  });
}
