import type { ChatMessageRequest, StoredMessage } from "../features/chat/types";
import type { ChatOverlayMessage } from "../features/chat/types/chatOverlay";
import { guestConversationContext, overlaySuggestions } from "../features/chat/overlay-context";
import { ChatApiError, getConversationDetail, sendChatMessage } from "./chatService";

export type HeritageChatContext = Pick<ChatMessageRequest, "heritage_id" | "heritage_context" | "scene_context">;

export function sendHeritageChatMessage(
  message: string, conversationId: string | null, context: HeritageChatContext,
  history: ChatOverlayMessage[], accessToken: string | null, signal?: AbortSignal,
) {
  return sendChatMessage({
    message, ...context, conversation_id: accessToken ? conversationId : null,
    ...(!accessToken ? { conversation_context: guestConversationContext(history) } : {}),
  }, accessToken, signal);
}

function restoredMessage(message: StoredMessage): ChatOverlayMessage {
  return {
    id: message.id, role: message.role, content: message.content,
    createdAt: message.created_at, citations: message.citations,
    needsUserChoice: message.needs_user_choice, abstained: message.abstained,
    answerType: message.answer_type, suggestions: overlaySuggestions(message.suggestions),
  };
}

export async function getHeritageConversation(
  conversationId: string, accountId: string, heritageId: number | null,
  accessToken: string, signal?: AbortSignal,
): Promise<ChatOverlayMessage[]> {
  const detail = await getConversationDetail(conversationId, accessToken, signal);
  if (String(detail.account_id) !== accountId || detail.heritage_id !== heritageId) {
    throw new ChatApiError("Cuộc trò chuyện không thuộc tài khoản hoặc di sản hiện tại.", 403);
  }
  return detail.messages.map(restoredMessage);
}
