import type { ChatMessageRequest, ChatSuggestion } from "./types";
import type { ChatOverlayMessage, ChatOverlaySuggestion } from "./types/chatOverlay";

/** Only actual completed turns qualify as guest prompt context, never the UI greeting. */
export function guestConversationContext(messages: ChatOverlayMessage[]): NonNullable<ChatMessageRequest["conversation_context"]> {
  const history = messages.filter((message) => message.id !== "mila-welcome")
    .slice(-6).map(({ role, content }) => ({ role, content: content.slice(0, 2000).trim() }))
    .filter((message) => message.content.length > 0);
  while (history.reduce((size, message) => size + message.content.length, 0) > 6000) history.shift();
  while (history[0]?.role === "assistant") history.shift();
  return history;
}

export function overlaySuggestions(suggestions: ChatSuggestion[] = []): ChatOverlaySuggestion[] {
  const options = suggestions.map((item) => item.suggested ?? item.label ?? item.title ?? item.name ?? "")
    .map((label) => label.trim()).filter(Boolean);
  return [...new Set(options)].slice(0, 6).map((value) => ({ label: value, value }));
}
