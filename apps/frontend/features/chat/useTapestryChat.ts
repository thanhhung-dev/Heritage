"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatOverlayMessage } from "@/features/chat/types/chatOverlay";
import { HeritageChatError, sendHeritageChatMessage } from "@/services/heritageChatService";

function welcome(): ChatOverlayMessage {
  return { id: "mila-welcome", role: "assistant", content: "Hi, I’m Mila, your AI heritage guide. What would you like to discover?",
    createdAt: new Date().toISOString(), citations: [] };
}

export function useTapestryChat(accessToken: string | null) {
  const [messages, setMessages] = useState<ChatOverlayMessage[]>(() => [welcome()]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const request = useRef<AbortController | null>(null);
  const timer = useRef<number | null>(null);

  const cancel = useCallback(() => {
    request.current?.abort();
    request.current = null;
    if (timer.current !== null) window.clearTimeout(timer.current);
    timer.current = null;
  }, []);
  useEffect(() => cancel, [cancel]);

  const send = useCallback(async (text?: string) => {
    const message = (text ?? input).trim();
    if (!message || request.current) return;
    const controller = new AbortController();
    request.current = controller;
    const user: ChatOverlayMessage = { id: crypto.randomUUID(), role: "user", content: message, createdAt: new Date().toISOString(), citations: [] };
    setMessages((previous) => [...previous, user]);
    setInput(""); setError(null); setSending(true);
    timer.current = window.setTimeout(() => controller.abort("timeout"), 35000);
    try {
      const answer = await sendHeritageChatMessage(message, accessToken, controller.signal);
      if (!controller.signal.aborted) setMessages((previous) => [...previous, answer]);
    } catch (failure) {
      if (controller.signal.aborted && controller.signal.reason !== "timeout") return;
      setMessages((previous) => previous.filter((item) => item.id !== user.id));
      setInput((draft) => draft || message);
      setError(controller.signal.reason === "timeout" ? "AI phản hồi quá thời gian. Vui lòng thử lại."
        : failure instanceof HeritageChatError ? failure.message : "Không thể kết nối tới máy chủ chat. Vui lòng thử lại.");
    } finally {
      if (request.current === controller) { cancel(); setSending(false); }
    }
  }, [input, accessToken, cancel]);

  const newConversation = useCallback(() => {
    cancel(); setSending(false); setMessages([welcome()]); setInput(""); setError(null);
  }, [cancel]);
  return { messages, input, setInput, sending, error, send, newConversation };
}
