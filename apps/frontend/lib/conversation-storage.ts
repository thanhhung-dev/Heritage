import { buildApiUrl } from "./api";

export function isConversationId(value: unknown): value is string {
  return (
    typeof value === "string" &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
  );
}

function key(account: string, scope: string): string {
  return `heritage:conversation:${encodeURIComponent(account)}:${encodeURIComponent(scope)}`;
}

export function readConversationId(
  storage: Pick<Storage, "getItem">,
  account: string | null,
  scope: string,
): string | null {
  if (!account) return null;
  try {
    const value = storage.getItem(key(account, scope));
    return isConversationId(value) ? value : null;
  } catch {
    return null;
  }
}

export function saveConversationId(
  storage: Pick<Storage, "setItem" | "removeItem">,
  account: string | null,
  scope: string,
  id: string | null,
): void {
  if (!account) return;
  try {
    if (isConversationId(id)) {
      storage.setItem(key(account, scope), id);
    } else {
      storage.removeItem(key(account, scope));
    }
  } catch {
    /* Browser storage is optional; the in-memory conversation still works. */
  }
}

export interface ConversationHistoryOptions {
  id?: string;
  method?: "GET" | "DELETE";
  limit?: number;
  offset?: number;
}

export interface ConversationHistoryDependencies {
  accessToken?: string | null;
  signal?: AbortSignal;
  fetchImpl?: typeof fetch;
}

/**
 * Read/delete owned history. A conversation UUID alone is never authentication.
 */
export function requestConversationHistory(
  apiUrl: string,
  options: ConversationHistoryOptions,
  dependencies: ConversationHistoryDependencies = {},
): Promise<Response> {
  if (!dependencies.accessToken) {
    throw new Error("Bạn cần đăng nhập để xem lịch sử chat.");
  }
  if (options.id !== undefined && !isConversationId(options.id)) {
    throw new Error("Mã hội thoại không hợp lệ.");
  }

  const suffix = options.id ? `/${options.id}${options.method === "DELETE" ? "" : "/messages"}` : "";
  const query = new URLSearchParams();
  if (options.limit !== undefined) query.set("limit", String(options.limit));
  if (options.offset !== undefined) query.set("offset", String(options.offset));

  const queryString = query.toString();
  return (dependencies.fetchImpl ?? fetch)(
    `${buildApiUrl(`/chat/conversations${suffix}`, apiUrl)}${queryString ? `?${queryString}` : ""}`,
    {
      method: options.method ?? "GET",
      headers: { Authorization: `Bearer ${dependencies.accessToken}` },
      signal: dependencies.signal,
    },
  );
}
