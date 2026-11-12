"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getAccessToken, getUser } from "@/lib/auth";
import { createConversationContext } from "@/lib/scene-chat-request";
import {
  sendChatMessage,
  type ChatMessageRequest,
} from "@/services/chatService";
import type { Message } from "@/features/chat/types";

export function getConversationAccountId(): string | null {
  return getAccessToken() ? getUser()?.account_id ?? null : null;
}

export function useConversationSession({
  scope,
  initialMessages,
  context = {},
  disabled = false,
}: {
  scope: string;
  initialMessages: () => Message[];
  context?: Omit<ChatMessageRequest, "message" | "conversation_context">;
  disabled?: boolean;
}) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [completedStoryIds, setCompletedStoryIds] = useState<string[]>([]);
  const owner = useRef(getConversationAccountId()).current;
  const pending = useRef<AbortController | null>(null);

  const startNewConversation = useCallback(() => {
    pending.current?.abort();
    pending.current = null;
    setMessages(initialMessages());
    setInput("");
    setSending(false);
    setError(null);
    setCompletedStoryIds([]);
  }, [initialMessages]);

  useEffect(() => {
    startNewConversation();
    return () => pending.current?.abort();
  }, [scope, startNewConversation]);

  const send = useCallback(
    async (text?: string, storyId?: string) => {
      const content = (text ?? input).trim();
      if (!content || disabled || pending.current || getConversationAccountId() !== owner) return;
      const controller = new AbortController();
      pending.current = controller;
      let timedOut = false;
      const timeout = window.setTimeout(() => { timedOut = true; controller.abort(); }, 35_000);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "user",
          content,
          createdAt: new Date().toISOString(),
        },
      ]);
      setInput("");
      setSending(true);
      setError(null);
      const isCurrent = () =>
        !controller.signal.aborted &&
        pending.current === controller &&
        getConversationAccountId() === owner;
      try {
        const response = await sendChatMessage(
          {
            ...context,
            ...(context.tour_context ? { tour_context: {
              ...context.tour_context, story_id: storyId ?? null, completed_story_ids: [...completedStoryIds],
            } } : {}),
            message: content,
            conversation_context: createConversationContext(
              messages.filter((message) => message.id !== "mila-welcome"),
            ),
          },
          controller.signal,
        );
        if (!isCurrent()) return;
        if (response.answerType === "answered" && storyId && response.replyContext?.story_id === storyId) {
          setCompletedStoryIds((previous) => [...previous.filter((id) => id !== storyId), storyId].slice(-32));
        }
        setMessages((current) => [
          ...current,
          {
            id: response.messageId,
            role: "assistant",
            content: response.answer,
            sources: response.sources,
            createdAt: new Date().toISOString(),
            correctedFrom: response.correctedFrom,
            correctedTo: response.correctedTo,
            answerType: response.answerType,
            needsUserChoice: response.needsUserChoice,
            abstained: response.abstained,
            replyContext: response.replyContext,
          },
        ]);
      } catch (failure) {
        if (timedOut && pending.current === controller && getConversationAccountId() === owner) {
          setError("AI phản hồi quá thời gian chờ. Bạn có thể gửi lại; yêu cầu trước có thể đã được máy chủ xử lý.");
        } else if (isCurrent()) {
          setError(
            failure instanceof Error ? failure.message : "Không thể gửi câu hỏi. Vui lòng thử lại.",
          );
        }
      } finally {
        window.clearTimeout(timeout);
        if (pending.current === controller) {
          pending.current = null;
          setSending(false);
        }
      }
    },
    [context, disabled, input, messages, owner, completedStoryIds],
  );

  return { messages, input, setInput, sending, error, send, startNewConversation, completedStoryIds };
}
