import { createConversationContext } from "@/lib/scene-chat-request";
import { ChatApiError, sendChatMessage, type ChatMessageRequest, type ChatReply } from "@/services/chatService";
import type { Message } from "./types";

export interface SceneChatContextMessage {
  role: "user" | "assistant";
  content: string;
}

export interface SceneChatRequest extends ChatMessageRequest {
  message: string;
  active_area_id: string;
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
  conversation_context?: SceneChatContextMessage[];
}

export type SceneChatResponse = ChatReply;
export { ChatApiError as SceneChatApiError };

export async function sendSceneChatMessage(request: SceneChatRequest, signal?: AbortSignal): Promise<SceneChatResponse> {
  return sendChatMessage(request, signal);
}

export function buildSceneConversationContext(messages: Message[]): SceneChatContextMessage[] {
  return createConversationContext(messages);
}
