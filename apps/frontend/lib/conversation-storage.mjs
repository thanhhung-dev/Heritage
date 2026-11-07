import { chatApiUrl } from "./chat-request.mjs";

/** @param {unknown} value @returns {value is string} */
export function isConversationId(value) {
  return typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

function key(account, scope) {
  return `heritage:conversation:${encodeURIComponent(account)}:${encodeURIComponent(scope)}`;
}

/** @param {Storage} storage @param {string | null} account @param {string} scope */
export function readConversationId(storage, account, scope) {
  if (!account) return null;
  try {
    const value = storage.getItem(key(account, scope));
    return isConversationId(value) ? value : null;
  } catch { return null; }
}

/** @param {Storage} storage @param {string | null} account @param {string} scope @param {string | null} id */
export function saveConversationId(storage, account, scope, id) {
  if (!account) return;
  try {
    if (isConversationId(id)) storage.setItem(key(account, scope), id);
    else storage.removeItem(key(account, scope));
  } catch { /* Browser storage is optional; the in-memory conversation still works. */ }
}

/**
 * Read/delete owned history. A conversation UUID alone is never authentication.
 * @param {string} apiUrl
 * @param {{id?: string, method?: 'GET' | 'DELETE', limit?: number, offset?: number}} options
 * @param {{accessToken?: string | null, signal?: AbortSignal, fetchImpl?: typeof fetch}} dependencies
 */
export function requestConversationHistory(apiUrl, options, dependencies = {}) {
  if (!dependencies.accessToken) throw new Error("Bạn cần đăng nhập để xem lịch sử chat.");
  if (options.id !== undefined && !isConversationId(options.id)) throw new Error("Mã hội thoại không hợp lệ.");
  const suffix = options.id ? `/${options.id}${options.method === "DELETE" ? "" : "/messages"}` : "";
  const query = new URLSearchParams();
  if (options.limit !== undefined) query.set("limit", String(options.limit));
  if (options.offset !== undefined) query.set("offset", String(options.offset));
  return (dependencies.fetchImpl ?? fetch)(
    `${chatApiUrl(apiUrl, `/chat/conversations${suffix}`)}${query.size ? `?${query}` : ""}`,
    { method: options.method ?? "GET", headers: { Authorization: `Bearer ${dependencies.accessToken}` }, signal: dependencies.signal },
  );
}
