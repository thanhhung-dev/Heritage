import { API_BASE_URL } from "@/config/api";
import { getAccessToken } from "@/lib/auth";
import { parseApiResponse, ApiError } from "@/lib/api";
import { isConversationId, requestConversationHistory } from "@/lib/conversation-storage";
import { requestSceneChat } from "@/lib/scene-chat-request";
import { safeSourceUrl } from "@/lib/safe-source-url";
import { validateTourReply } from "@/lib/tour-chat-scope";
import type { Message, Source, TourChatContext, TourReplyContext } from "@/features/chat/types";

export interface ChatContextMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatMessageRequest {
  message: string;
  conversation_context?: ChatContextMessage[];
  active_area_id?: string;
  heritage_id?: number;
  heritage_context?: string | Record<string, unknown>;
  scene_context?: string | Record<string, unknown> | null;
  tour_context?: TourChatContext;
}

export interface ChatReply {
  messageId: string;
  answer: string;
  sources: Source[];
  followUpQuestions: string[];
  correctedFrom?: string;
  correctedTo?: string;
  answerType?: string;
  needsUserChoice: boolean;
  abstained: boolean;
  replyContext?: TourReplyContext;
}

export interface ConversationSummary {
  id: string;
  title: string;
  heritage_id: number | null;
  active_area_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationHistory {
  id: string;
  activeAreaId: string | null;
  messages: Message[];
  totalMessages: number;
}

/**
 * Standard Chat API Error for backward compatibility.
 */
export class ChatApiError extends ApiError {
  constructor(message: string, status: number) {
    super(message, status);
    this.name = "ChatApiError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function sourcesFrom(value: unknown): Source[] {
  if (!Array.isArray(value)) throw new ChatApiError("Trích dẫn từ máy chủ không đúng định dạng.", 502);
  return value.flatMap((source): Source[] => {
    if (!isRecord(source)) return [];
    const id = source.chunk_id ?? source.passage_id ?? source.id;
    return [{
      doc: typeof source.doc === "string" ? source.doc : undefined,
      heading: typeof source.heading === "string" ? source.heading : undefined,
      text: typeof source.text === "string" ? source.text : undefined,
      url: safeSourceUrl(typeof source.url === "string" ? source.url : null) ?? undefined,
      chunk_id: typeof id === "string" || typeof id === "number" ? String(id) : undefined,
    }];
  });
}

function replyContextFrom(value: unknown): TourReplyContext | undefined {
  if (value == null) return undefined;
  if (!isRecord(value) || !Number.isInteger(value.scene_id) || Number(value.scene_id) <= 0
      || typeof value.scene_key !== "string" || !value.scene_key || value.scene_key.length > 80
      || typeof value.scene_title !== "string" || !value.scene_title || value.scene_title.length > 200
      || !["scene", "standard", "free", "walk"].includes(String(value.mode))
      || (value.highlight_id != null && (!Number.isInteger(value.highlight_id) || Number(value.highlight_id) <= 0))
      || (value.highlight_title != null && (typeof value.highlight_title !== "string" || value.highlight_title.length > 200))
      || (value.story_id != null && (typeof value.story_id !== "string" || !value.story_id || value.story_id.length > 80))) {
    throw new ChatApiError("Máy chủ trả ngữ cảnh tham quan không hợp lệ.", 502);
  }
  return value as unknown as TourReplyContext;
}

function outcomeFrom(data: Record<string, unknown>) {
  return {
    correctedFrom: typeof data.corrected_from === "string" ? data.corrected_from : undefined,
    correctedTo: typeof data.corrected_to === "string" ? data.corrected_to : undefined,
    answerType: typeof data.answer_type === "string" ? data.answer_type : undefined,
    needsUserChoice: data.needs_user_choice === true,
    abstained: data.abstained === true,
    replyContext: replyContextFrom(data.reply_context),
  };
}

export async function sendChatMessage(request: ChatMessageRequest, signal?: AbortSignal): Promise<ChatReply> {
  const response = await requestSceneChat(API_BASE_URL, request, { accessToken: getAccessToken(), signal });
  const data = await parseApiResponse<Record<string, unknown>>(response);

  if (!isRecord(data) || typeof data.answer !== "string") {
    throw new ChatApiError("Phản hồi chat không đúng định dạng.", 502);
  }
  const outcome = outcomeFrom(data);
  if (request.tour_context) {
    const expected = request.tour_context;
    const actual = outcome.replyContext;
    if (!actual || actual.scene_id !== expected.scene_id || actual.mode !== expected.mode
        || (actual.highlight_id ?? null) !== (expected.highlight_id ?? null)
        || (actual.story_id != null && actual.story_id !== expected.story_id)) {
      throw new ChatApiError("Máy chủ chưa xác nhận đúng ngữ cảnh của câu hỏi. Vui lòng cập nhật backend.", 502);
    }
  }

  const messageId = isConversationId(data.message_id)
    ? data.message_id
    : crypto.randomUUID();

  const followUpQuestions =
    request.active_area_id && data.active_area_id
      ? validateTourReply(data, request.active_area_id)
      : Array.isArray(data.follow_up_questions)
        ? data.follow_up_questions.filter((item): item is string => typeof item === "string").slice(0, 3)
        : Array.isArray(data.suggestions)
          ? data.suggestions.filter((item): item is string => typeof item === "string").slice(0, 3)
          : [];

  return {
    messageId,
    answer: data.answer,
    sources: sourcesFrom(data.sources),
    followUpQuestions,
    ...outcome,
  };
}

export async function listConversations(signal?: AbortSignal): Promise<ConversationSummary[]> {
  const response = await requestConversationHistory(API_BASE_URL, { limit: 100 }, { accessToken: getAccessToken(), signal });
  const data = await parseApiResponse<unknown>(response);
  if (!Array.isArray(data)) throw new ChatApiError("Danh sách hội thoại không đúng định dạng.", 502);
  return data.filter((row): row is ConversationSummary => isRecord(row) && isConversationId(row.id) && typeof row.title === "string");
}

export async function getConversationHistory(id: string, signal?: AbortSignal, offset = 0): Promise<ConversationHistory> {
  const response = await requestConversationHistory(API_BASE_URL, { id, limit: 100, offset }, { accessToken: getAccessToken(), signal });
  const data = await parseApiResponse<Record<string, unknown>>(response);

  if (!isRecord(data) || data.id !== id || !Array.isArray(data.messages) || typeof data.total_messages !== "number") {
    throw new ChatApiError("Lịch sử chat không đúng định dạng.", 502);
  }

  const messages = data.messages.map((row): Message => {
    if (!isRecord(row) || !isConversationId(row.id) || row.conversation_id !== id
        || (row.role !== "user" && row.role !== "assistant") || typeof row.content !== "string") {
      throw new ChatApiError("Tin nhắn trong lịch sử không đúng định dạng.", 502);
    }
    return {
      id: row.id,
      role: row.role,
      content: row.content,
      sources: sourcesFrom(row.sources),
      createdAt: typeof row.created_at === "string" ? row.created_at : undefined,
      ...outcomeFrom(row),
    };
  });

  return {
    id,
    activeAreaId: typeof data.active_area_id === "string" ? data.active_area_id : null,
    messages,
    totalMessages: data.total_messages,
  };
}

export async function deleteConversation(id: string, signal?: AbortSignal): Promise<void> {
  const response = await requestConversationHistory(API_BASE_URL, { id, method: "DELETE" }, { accessToken: getAccessToken(), signal });
  if (!response.ok) {
    await parseApiResponse(response);
  }
}
