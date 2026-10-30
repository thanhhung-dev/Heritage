import { z } from "zod";
import { API_BASE_URL } from "../config/api";
import { requestChat } from "../lib/chat-request.mjs";
import { safeSourceUrl } from "../lib/safe-source-url";
import type { ChatOverlayMessage } from "../features/chat/types/chatOverlay";

const optionalText = z.string().nullish();
const replySchema = z.object({
  answer: z.string(),
  sources: z.array(z.object({
    doc: optionalText, title: optionalText, source_title: optionalText,
    url: optionalText, source_url: optionalText, score: z.number().nullish(),
  })).default([]),
  needs_user_choice: z.boolean().optional(), abstained: z.boolean().optional(),
  answer_type: optionalText,
  suggestions: z.array(z.object({
    suggested: optionalText, label: optionalText, title: optionalText, name: optionalText,
  })).default([]),
});

export class HeritageChatError extends Error {
  constructor(message: string, public readonly status: number) { super(message); this.name = "HeritageChatError"; }
}

/** This branch exposes POST /api/chat; keep its real contract instead of inventing persisted UUIDs. */
export async function sendHeritageChatMessage(message: string, accessToken: string | null, signal: AbortSignal): Promise<ChatOverlayMessage> {
  const response = await requestChat(API_BASE_URL, message, { accessToken, signal });
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : null;
    throw new HeritageChatError(typeof detail === "string" ? detail : "Không thể xử lý yêu cầu chat. Vui lòng thử lại.", response.status);
  }
  const result = replySchema.safeParse(data);
  if (!result.success) throw new HeritageChatError("Phản hồi chat không đúng định dạng. Vui lòng thử lại.", response.status);
  const reply = result.data;
  const id = crypto.randomUUID();
  const labels = reply.suggestions.map((item) => item.suggested ?? item.label ?? item.title ?? item.name ?? "").map((label) => label.trim()).filter(Boolean);
  return {
    id, role: "assistant", content: reply.answer, createdAt: new Date().toISOString(),
    citations: reply.sources.map((source, index) => ({
      id: `${id}-source-${index}`, message_id: id,
      source_title: source.source_title ?? source.doc ?? source.title ?? "Nguồn tham khảo",
      source_url: safeSourceUrl(source.source_url ?? source.url ?? null), relevance_score: source.score ?? null,
    })),
    needsUserChoice: reply.needs_user_choice,
    abstained: reply.abstained || reply.answer_type === "insufficient_evidence", answerType: reply.answer_type,
    suggestions: [...new Set(labels)].slice(0, 6).map((value) => ({ label: value, value })),
  };
}
