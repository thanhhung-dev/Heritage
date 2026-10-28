"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessageRequest } from "@/features/chat/types";
import type { ChatOverlayMessage } from "@/features/chat/types/chatOverlay";
import { chatErrorMessage, sendChatMessage } from "@/services/chatService";

function welcome(): ChatOverlayMessage {
  return {
    id: "mila-welcome", role: "assistant", createdAt: new Date().toISOString(), citations: [],
    content: "Hi, I’m Mila, your AI heritage guide. What would you like to discover?",
    suggestions: [
      { label: "Explore this heritage", value: "Give me a short introduction to this heritage." },
      { label: "History & origins", value: "Tell me about the history and origins of this heritage." },
      { label: "About this scene", value: "What am I looking at in this scene?" },
      { label: "Architectural details", value: "Which architectural details should I look for here?" },
    ],
  };
}

type OverlayContext = Pick<ChatMessageRequest, "heritage_id" | "heritage_context" | "scene_context">;

export function useChatOverlay(accessToken: string | null, context: OverlayContext) {
  const [messages, setMessages] = useState<ChatOverlayMessage[]>(() => [welcome()]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeRequest = useRef<AbortController | null>(null);
  const busy = useRef(false);
  const timeout = useRef<number | null>(null);
  const latestContext = useRef(context);
  latestContext.current = context;

  useEffect(() => () => {
    activeRequest.current?.abort();
    if (timeout.current !== null) window.clearTimeout(timeout.current);
  }, []);

  const send = useCallback(async (text?: string) => {
    const message = (text ?? input).trim();
    if (!message || busy.current) return;
    const controller = new AbortController();
    activeRequest.current = controller;
    busy.current = true;
    const userMessage: ChatOverlayMessage = {
      id: crypto.randomUUID(), role: "user", content: message,
      createdAt: new Date().toISOString(), citations: [],
    };
    setMessages((previous) => [...previous, userMessage]);
    setInput("");
    setError(null);
    setSending(true);
    timeout.current = window.setTimeout(() => controller.abort("timeout"), 35000);
    try {
      const response = await sendChatMessage({
        message, conversation_id: conversationId, ...latestContext.current,
      }, accessToken, controller.signal);
      if (controller.signal.aborted) return;
      setConversationId(accessToken ? response.conversation_id : null);
      setMessages((previous) => [...previous, {
        id: response.message_id, role: "assistant", content: response.answer,
        createdAt: new Date().toISOString(), citations: response.citations,
      }]);
    } catch (failure) {
      if (controller.signal.aborted && controller.signal.reason !== "timeout") return;
      setMessages((previous) => previous.filter((item) => item.id !== userMessage.id));
      setInput(message);
      setError(controller.signal.reason === "timeout"
        ? "The assistant took too long. Please try again."
        : chatErrorMessage(failure));
    } finally {
      if (activeRequest.current === controller) {
        if (timeout.current !== null) window.clearTimeout(timeout.current);
        timeout.current = null;
        activeRequest.current = null;
        busy.current = false;
        setSending(false);
      }
    }
  }, [accessToken, conversationId, input]);

  const newConversation = useCallback(() => {
    activeRequest.current?.abort();
    activeRequest.current = null;
    if (timeout.current !== null) window.clearTimeout(timeout.current);
    timeout.current = null;
    busy.current = false;
    setSending(false);
    setMessages([welcome()]);
    setConversationId(null);
    setInput("");
    setError(null);
  }, []);

  return { messages, input, setInput, sending, error, send, newConversation };
}
