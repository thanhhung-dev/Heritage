"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  chatErrorMessage, citationSources, getConversationMessages, listConversations, sendChatMessage,
} from "@/services/chatService";
import type { Conversation, Message } from "./types";

export function useChatConversations(accessToken: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [reading, setReading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const activeRequest = useRef<AbortController | null>(null);
  const listRequest = useRef<AbortController | null>(null);
  const busy = useRef(false);
  const historyOffset = useRef(0);

  const refreshHistory = useCallback(async (append = false) => {
    if (!accessToken) return;
    listRequest.current?.abort();
    const controller = new AbortController();
    listRequest.current = controller;
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const offset = append ? historyOffset.current : 0;
      const rows = await listConversations(accessToken, offset, controller.signal);
      if (controller.signal.aborted) return;
      setConversations((current) => append ? [...new Map([...current, ...rows].map((row) => [row.id, row])).values()] : rows);
      historyOffset.current = offset + rows.length;
      setHasMore(rows.length === 50);
    } catch (failure) {
      if (!controller.signal.aborted) setHistoryError(chatErrorMessage(failure));
    } finally {
      if (!controller.signal.aborted) setHistoryLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    void refreshHistory();
    return () => {
      activeRequest.current?.abort();
      listRequest.current?.abort();
    };
  }, [refreshHistory]);

  const send = useCallback(async (text?: string) => {
    const message = (text ?? input).trim();
    if (!message || busy.current) return;
    busy.current = true;
    const controller = new AbortController();
    activeRequest.current = controller;
    const temporaryId = crypto.randomUUID();
    setMessages((current) => [...current, { id: temporaryId, role: "user", content: message }]);
    setInput("");
    setError(null);
    setSending(true);
    const timeout = window.setTimeout(() => controller.abort("timeout"), 35000);
    try {
      const response = await sendChatMessage({ message, conversation_id: conversationId }, accessToken, controller.signal);
      if (controller.signal.aborted) return;
      setConversationId(accessToken ? response.conversation_id : null);
      setMessages((current) => [...current, {
        id: response.message_id, role: "assistant", content: response.answer,
        sources: citationSources(response.citations),
      }]);
      void refreshHistory();
    } catch (failure) {
      if (controller.signal.aborted && controller.signal.reason !== "timeout") return;
      setMessages((current) => current.filter((item) => item.id !== temporaryId));
      setInput(message);
      setError(controller.signal.reason === "timeout"
        ? "Máy chủ xử lý quá thời gian. Vui lòng thử lại."
        : chatErrorMessage(failure));
    } finally {
      window.clearTimeout(timeout);
      if (activeRequest.current === controller) {
        busy.current = false;
        setSending(false);
      }
    }
  }, [input, conversationId, accessToken, refreshHistory]);

  const selectConversation = useCallback(async (id: string) => {
    if (!accessToken || busy.current) return;
    busy.current = true;
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setReading(true);
    setError(null);
    try {
      const rows = await getConversationMessages(id, accessToken, controller.signal);
      if (controller.signal.aborted) return;
      setMessages(rows);
      setConversationId(id);
      setInput("");
    } catch (failure) {
      if (!controller.signal.aborted) setError(chatErrorMessage(failure));
    } finally {
      if (activeRequest.current === controller) {
        busy.current = false;
        setReading(false);
      }
    }
  }, [accessToken]);

  const newConversation = useCallback(() => {
    if (busy.current) return;
    activeRequest.current?.abort();
    setMessages([]);
    setConversationId(null);
    setInput("");
    setError(null);
    setReading(false);
  }, []);

  return {
    messages, input, setInput, conversationId, sending, reading, error,
    conversations, historyError, historyLoading, hasMore,
    send, selectConversation, newConversation, refreshHistory,
  };
}
