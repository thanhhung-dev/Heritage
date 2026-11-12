import { apiFetch, type ApiDependencies } from "./api";

export interface ConversationContextMessage {
  role: "user" | "assistant";
  content: string;
}

export type SceneChatDependencies = ApiDependencies;

/**
 * Build bounded client history for each transient chat request.
 */
export function createConversationContext(
  messages: Array<{ role: "user" | "assistant" | string; content: string }>,
): ConversationContextMessage[] {
  const recentMessages = messages
    .filter(
      (message): message is ConversationContextMessage =>
        (message.role === "user" || message.role === "assistant") &&
        typeof message.content === "string" &&
        message.content.trim().length > 0,
    )
    .slice(-6);

  let totalCharacters = 0;
  const boundedMessages: ConversationContextMessage[] = [];

  for (const message of [...recentMessages].reverse()) {
    const remainingCharacters = 6000 - totalCharacters;
    if (remainingCharacters <= 0) break;

    const content = message.content.trim().slice(0, Math.min(2000, remainingCharacters));
    if (!content) continue;

    boundedMessages.push({ role: message.role, content });
    totalCharacters += content.length;
  }

  return boundedMessages.reverse();
}

/**
 * Send chat context without creating or resuming a persisted conversation.
 */
export function requestSceneChat(
  apiUrl: string,
  request: unknown,
  dependencies: SceneChatDependencies = {},
): Promise<Response> {
  return apiFetch(
    "/chat",
    {
      method: "POST",
      body: JSON.stringify(request),
    },
    dependencies,
    apiUrl,
  );
}
