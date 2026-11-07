"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getAccessToken, getUser } from "@/lib/auth";
import { readConversationId, saveConversationId } from "@/lib/conversation-storage";
import { createConversationContext } from "@/lib/scene-chat-request";
import {
  ChatApiError,
  getConversationHistory,
  sendChatMessage,
  type ChatMessageRequest,
} from "@/services/chatService";
import type { Message } from "@/features/chat/types";

export function getConversationAccountId(): string | null {
  return getAccessToken() ? getUser()?.account_id ?? null : null;
}

function pointer(owner: string | null, scope: string, id: string | null): void {
  try {
    saveConversationId(window.localStorage, owner, scope, id);
  } catch {
    /* Storage is optional. */
  }
}

export function useConversationSession({
  scope,
  initialMessages,
  context = {},
  disabled = false,
}: {
  scope: string;
  initialMessages: () => Message[];
  context?: Omit<ChatMessageRequest, "message" | "conversation_id" | "conversation_context">;
  disabled?: boolean;
}) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const owner = useRef(getConversationAccountId()).current;
  const conversation = useRef<string | null>(null);
  const pending = useRef<AbortController | null>(null);
  const area = context.active_area_id ?? null;

  useEffect(() => {
    if (!owner || disabled) return;
    let id: string | null = null;
    try {
      id = readConversationId(window.localStorage, owner, scope);
    } catch {
      return;
    }
    if (!id) return;
    const controller = new AbortController();
    pending.current = controller;
    setRestoring(true);
    void (async () => {
      try {
        let detail = await getConversationHistory(id, controller.signal);
        if (detail.totalMessages > 100) {
          detail = await getConversationHistory(id, controller.signal, detail.totalMessages - 100);
        }
        if (
          controller.signal.aborted ||
          getConversationAccountId() !== owner ||
          pending.current !== controller
        ) {
          return;
        }
        if (detail.activeAreaId !== area) {
          pointer(owner, scope, null);
          throw new ChatApiError(
            "Hội thoại đã lưu không thuộc khu vực hiện tại. Hãy bắt đầu hội thoại mới.",
            400,
          );
        }
        conversation.current = detail.id;
        setMessages(detail.messages.length ? detail.messages : initialMessages());
      } catch (failure) {
        if (
          controller.signal.aborted ||
          getConversationAccountId() !== owner ||
          pending.current !== controller
        ) {
          return;
        }
        if (failure instanceof ChatApiError && [401, 403, 404].includes(failure.status)) {
          pointer(owner, scope, null);
        }
        setError(failure instanceof Error ? failure.message : "Không thể khôi phục lịch sử chat.");
      } finally {
        if (pending.current === controller) {
          pending.current = null;
          setRestoring(false);
        }
      }
    })();
    return () => controller.abort();
  }, [area, disabled, initialMessages, owner, scope]);

  useEffect(() => () => pending.current?.abort(), []);

  const startNewConversation = useCallback(() => {
    pending.current?.abort();
    pending.current = null;
    conversation.current = null;
    pointer(owner, scope, null);
    setMessages(initialMessages());
    setInput("");
    setSending(false);
    setRestoring(false);
    setError(null);
  }, [initialMessages, owner, scope]);

  const send = useCallback(
    async (text?: string) => {
      const content = (text ?? input).trim();
      if (!content || disabled || pending.current || getConversationAccountId() !== owner) return;
      const controller = new AbortController();
      pending.current = controller;
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
            message: content,
            ...(owner && conversation.current
              ? { conversation_id: conversation.current }
              : {
                  conversation_context: createConversationContext(
                    messages.filter((message) => message.id !== "mila-welcome"),
                  ),
                }),
          },
          controller.signal,
        );
        if (!isCurrent()) return;
        if (owner) {
          conversation.current = response.conversationId;
          pointer(owner, scope, response.conversationId);
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
          },
        ]);
      } catch (failure) {
        if (isCurrent()) {
          setError(
            failure instanceof Error ? failure.message : "Không thể gửi câu hỏi. Vui lòng thử lại.",
          );
        }
      } finally {
        if (pending.current === controller) {
          pending.current = null;
          setSending(false);
        }
      }
    },
    [context, disabled, input, messages, owner, scope],
  );

  return { messages, input, setInput, sending, restoring, error, send, startNewConversation };
}
