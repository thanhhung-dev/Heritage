import { z } from "zod";
import { API_BASE_URL } from "../config/api";
import { chatApiUrl, requestChat } from "../lib/chat-request.mjs";
import { safeSourceUrl } from "../lib/safe-source-url";
import type {
  ChatMessageRequest, ChatResponse, Conversation, Message, MessageCitation, StoredMessage,
} from "../features/chat/types";

const citationSchema = z.object({
  id: z.string(), message_id: z.string(), source_title: z.string(),
  source_url: z.string().nullable(), relevance_score: z.number().nullable(),
});
const conversationSchema = z.object({
  id: z.string(), account_id: z.number().nullable(), title: z.string(),
  heritage_id: z.number().nullable(), created_at: z.string(), updated_at: z.string(),
});
const outcomeFields = {
  corrected_from: z.string().optional(), corrected_to: z.string().optional(),
  needs_user_choice: z.boolean().optional(),
  suggestions: z.array(z.object({
    original: z.string().optional(), suggested: z.string().optional(), label: z.string().optional(),
    title: z.string().optional(), name: z.string().optional(), score: z.number().optional(),
  })).optional(),
  entity_id: z.string().nullable().optional(), intent: z.string().nullable().optional(),
  resolution_status: z.string().nullable().optional(), answer_type: z.string().nullable().optional(),
  abstained: z.boolean().optional(),
  abstention_reason: z.enum(["insufficient_evidence", "service_unavailable"]).nullable().optional(),
};
const storedMessageSchema = z.object({
  id: z.string(), conversation_id: z.string(), role: z.enum(["user", "assistant"]),
  content: z.string(), created_at: z.string(), citations: z.array(citationSchema), ...outcomeFields,
});
const chatResponseSchema = z.object({
  conversation_id: z.string(), message_id: z.string(), answer: z.string(),
  citations: z.array(citationSchema), ...outcomeFields,
});

export class ChatApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "ChatApiError";
  }
}

async function readResponse<T>(response: Response, schema: z.ZodType<T>): Promise<T> {
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401) {
      throw new ChatApiError("Phiên đăng nhập không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại.", 401);
    }
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : null;
    const fallback = response.status === 504
      ? "AI xử lý quá thời gian. Vui lòng thử lại."
      : "Không thể xử lý yêu cầu chat. Vui lòng thử lại.";
    throw new ChatApiError(typeof detail === "string" ? detail : fallback, response.status);
  }
  const parsed = schema.safeParse(data);
  if (!parsed.success) throw new ChatApiError("Phản hồi từ máy chủ không đúng định dạng chat.", response.status);
  return parsed.data;
}

function authenticatedHeaders(accessToken: string) {
  if (!accessToken) throw new ChatApiError("Vui lòng đăng nhập để xem lịch sử trò chuyện.", 401);
  return { Accept: "application/json", Authorization: `Bearer ${accessToken}` };
}

export async function sendChatMessage(
  request: ChatMessageRequest, accessToken: string | null, signal?: AbortSignal,
): Promise<ChatResponse> {
  const response = await requestChat(API_BASE_URL, {
    ...request,
    // The backend permits guest creation, but a UUID alone cannot resume guest history.
    conversation_id: accessToken ? request.conversation_id ?? null : null,
  }, { accessToken, signal });
  return readResponse(response, chatResponseSchema);
}

export async function listConversations(
  accessToken: string, offset = 0, signal?: AbortSignal,
): Promise<Conversation[]> {
  const response = await fetch(chatApiUrl(API_BASE_URL, `/conversations?limit=50&offset=${offset}`), {
    headers: authenticatedHeaders(accessToken), signal, cache: "no-store",
  });
  return readResponse(response, z.array(conversationSchema));
}

export async function getConversationMessages(
  conversationId: string, accessToken: string, signal?: AbortSignal,
): Promise<Message[]> {
  const messages: StoredMessage[] = [];
  const pageSize = 500;
  for (let offset = 0; ; offset += pageSize) {
    const response = await fetch(chatApiUrl(API_BASE_URL,
      `/conversations/${encodeURIComponent(conversationId)}/messages?limit=${pageSize}&offset=${offset}`), {
      headers: authenticatedHeaders(accessToken), signal, cache: "no-store",
    });
    const page = await readResponse(response, conversationSchema.extend({ messages: z.array(storedMessageSchema) }));
    messages.push(...page.messages);
    if (page.messages.length < pageSize) break;
  }
  return messages.map((message) => ({
    id: message.id, role: message.role, content: message.content,
    sources: citationSources(message.citations),
  }));
}

export function citationSources(citations: MessageCitation[]): NonNullable<Message["sources"]> {
  return citations.map((citation) => ({
    doc: citation.source_title,
    url: safeSourceUrl(citation.source_url) ?? undefined,
    chunk_id: citation.id,
  }));
}

export function chatErrorMessage(error: unknown): string {
  return error instanceof ChatApiError ? error.message
    : "Không thể kết nối tới máy chủ chat. Vui lòng kiểm tra kết nối và thử lại.";
}
