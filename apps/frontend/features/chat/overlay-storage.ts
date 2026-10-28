import { z } from "zod";
import type { ChatOverlayMessage } from "./types/chatOverlay";

export type ChatStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const cachedMessage = z.object({
  id: z.string().max(128), role: z.enum(["user", "assistant"]), content: z.string().max(16000),
  createdAt: z.string().datetime({ offset: true }),
  citations: z.array(z.object({
    id: z.string(), message_id: z.string(), source_title: z.string(),
    source_url: z.string().nullable(), relevance_score: z.number().nullable(),
  })).max(50),
  needsUserChoice: z.boolean().optional(), abstained: z.boolean().optional(),
  answerType: z.string().nullable().optional(),
  suggestions: z.array(z.object({ label: z.string(), value: z.string() })).max(6).optional(),
});

/** The unverified subject names a cache only. The API still validates every JWT. */
export function chatAccountId(token: string | null): string | null {
  if (!token) return null;
  try {
    const encoded = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const claims: unknown = JSON.parse(atob(encoded.padEnd(Math.ceil(encoded.length / 4) * 4, "=")));
    if (claims && typeof claims === "object" && "sub" in claims
      && typeof claims.sub === "string" && /^[1-9]\d*$/.test(claims.sub)) return claims.sub;
  } catch { /* Invalid credentials are handled by the API, never downgraded to Guest. */ }
  return null;
}

export function chatStorageKey(heritageScope: string, accountId: string | null): string {
  return `heritage.overlay.v1:${accountId ?? "guest"}:${encodeURIComponent(heritageScope)}`;
}

export function browserChatStorage(kind: "localStorage" | "sessionStorage"): ChatStorage | null {
  try { return typeof window === "undefined" ? null : window[kind]; } catch { return null; }
}

export function forgetChat(storage: ChatStorage | null, key: string) {
  try { storage?.removeItem(key); } catch { /* Chat also works without browser storage. */ }
}

export function rememberedConversation(storage: ChatStorage | null, key: string): string | null {
  try {
    const value = storage?.getItem(key);
    return value && uuid.test(value) ? value : null;
  } catch { return null; }
}

export function rememberConversation(storage: ChatStorage | null, key: string, id: string) {
  if (!uuid.test(id)) return;
  try { storage?.setItem(key, id); } catch { /* Keep the current conversation in memory. */ }
}

export function rememberedGuestMessages(storage: ChatStorage | null, key: string): ChatOverlayMessage[] {
  try {
    const raw = storage?.getItem(key);
    if (!raw || raw.length > 150000) return [];
    return z.array(cachedMessage).max(12).parse(JSON.parse(raw));
  } catch { return []; }
}

export function rememberGuestMessages(storage: ChatStorage | null, key: string, messages: ChatOverlayMessage[]) {
  const completed = messages.filter((message) => message.id !== "mila-welcome").slice(-12);
  while (completed.reduce((size, item) => size + item.content.length, 0) > 24000) completed.shift();
  while (completed[0]?.role === "assistant") completed.shift();
  if (!completed.length) return forgetChat(storage, key);
  try {
    const data = z.array(cachedMessage).max(12).parse(completed);
    storage?.setItem(key, JSON.stringify(data));
  } catch { /* Invalid or oversized history stays in memory only. */ }
}
