import { API_BASE_URL } from "@/config/api";
import { getAccessToken } from "@/lib/auth";
import {
  createConversationContext,
  requestSceneChat,
} from "@/lib/scene-chat-request.mjs";
import type { Message, Source } from "./types";

export interface SceneChatContextMessage {
  role: "user" | "assistant";
  content: string;
}

export interface SceneChatRequest {
  message: string;
  heritage_id?: number;
  heritage_context: {
    id: number;
    slug: string;
    title: string;
    region: string | null;
  };
  scene_context: {
    id: number;
    key: string;
    slug: string;
    title: string;
    description: string | null;
    sequence: number;
  } | null;
  conversation_id?: string;
  conversation_context?: SceneChatContextMessage[];
}

export interface SceneChatResponse {
  conversationId: string;
  answer: string;
  sources: Source[];
  correctedFrom?: string;
  correctedTo?: string;
}

export class SceneChatApiError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
    this.name = "SceneChatApiError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export async function sendSceneChatMessage(
  request: SceneChatRequest,
  signal?: AbortSignal,
): Promise<SceneChatResponse> {
  const response = await requestSceneChat(API_BASE_URL, request, {
    accessToken: getAccessToken(),
    signal,
  });
  const data: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const detail = isRecord(data) ? data.detail : undefined;
    let message = "Không thể gửi câu hỏi lúc này. Vui lòng thử lại.";
    if (response.status === 401) {
      message = "Phiên đăng nhập không hợp lệ hoặc đã hết hạn. Vui lòng đăng nhập lại.";
    } else if (response.status === 404) {
      message =
        "API chat theo ngữ cảnh chưa có trên máy chủ này. Vui lòng thử lại sau khi backend được cập nhật.";
    } else if (typeof detail === "string") {
      message = detail;
    }
    throw new SceneChatApiError(message, response.status);
  }

  if (
    !isRecord(data) ||
    typeof data.answer !== "string" ||
    typeof data.conversation_id !== "string"
  ) {
    throw new SceneChatApiError("Phản hồi từ máy chủ chat không đúng định dạng.", response.status);
  }

  const citations = Array.isArray(data.citations) ? data.citations : [];
  const sources = citations.flatMap((citation): Source[] => {
    if (!isRecord(citation)) return [];

    const source: Source = {};
    if (typeof citation.source_title === "string") source.doc = citation.source_title;
    if (
      typeof citation.source_url === "string" &&
      /^https?:\/\//i.test(citation.source_url)
    ) {
      source.url = citation.source_url;
    }
    if (typeof citation.id === "string") source.chunk_id = citation.id;
    return [source];
  });

  return {
    conversationId: data.conversation_id,
    answer: data.answer,
    sources,
    correctedFrom:
      typeof data.corrected_from === "string" ? data.corrected_from : undefined,
    correctedTo:
      typeof data.corrected_to === "string" ? data.corrected_to : undefined,
  };
}

export function buildSceneConversationContext(
  messages: Message[],
): SceneChatContextMessage[] {
  return createConversationContext(messages);
}
