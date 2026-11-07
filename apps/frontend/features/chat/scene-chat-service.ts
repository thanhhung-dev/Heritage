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
  conversationId: string | null;
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

  if (!isRecord(data) || typeof data.answer !== "string") {
    throw new SceneChatApiError("Phản hồi từ máy chủ chat không đúng định dạng.", response.status);
  }

  const rawSources = Array.isArray(data.sources)
    ? data.sources
    : Array.isArray(data.citations)
      ? data.citations
      : [];
  const sources = rawSources.flatMap((item): Source[] => {
    if (!isRecord(item)) return [];

    const source: Source = {};
    if (typeof item.doc === "string") {
      source.doc = item.doc;
    } else if (typeof item.source_title === "string") {
      source.doc = item.source_title;
    }
    if (typeof item.heading === "string") {
      source.heading = item.heading;
    }
    if (typeof item.text === "string") {
      source.text = item.text;
    }
    const rawUrl =
      typeof item.url === "string"
        ? item.url
        : typeof item.source_url === "string"
          ? item.source_url
          : null;
    if (rawUrl && /^https?:\/\//i.test(rawUrl)) {
      source.url = rawUrl;
    }
    if (typeof item.chunk_id === "string" || typeof item.chunk_id === "number") {
      source.chunk_id = String(item.chunk_id);
    } else if (typeof item.passage_id === "string" || typeof item.passage_id === "number") {
      source.chunk_id = String(item.passage_id);
    } else if (typeof item.id === "string" || typeof item.id === "number") {
      source.chunk_id = String(item.id);
    }
    return [source];
  });

  return {
    conversationId:
      typeof data.conversation_id === "string" ? data.conversation_id : null,
    answer: data.answer,
    sources,
    correctedFrom:
      typeof data.corrected_from === "string" && data.corrected_from
        ? data.corrected_from
        : undefined,
    correctedTo:
      typeof data.corrected_to === "string" && data.corrected_to
        ? data.corrected_to
        : undefined,
  };
}

export function buildSceneConversationContext(
  messages: Message[],
): SceneChatContextMessage[] {
  return createConversationContext(messages);
}
