"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatOverlayMessage } from "@/features/chat/types/chatOverlay";
import { overlaySuggestions } from "@/features/chat/overlay-context";
import { ChatApiError, chatErrorMessage } from "@/services/chatService";
import { getHeritageConversation, sendHeritageChatMessage, type HeritageChatContext } from "@/services/heritageChatService";
import {
  browserChatStorage, chatAccountId, chatStorageKey, forgetChat, rememberConversation,
  rememberedConversation, rememberedGuestMessages, rememberGuestMessages,
} from "@/features/chat/overlay-storage";

function welcome(): ChatOverlayMessage {
  return {
    id: "mila-welcome", role: "assistant", createdAt: new Date().toISOString(), citations: [],
    content: "Hi, I’m Mila, your AI heritage guide. What would you like to discover?",
  };
}

export function useChatOverlay(accessToken: string | null, context: HeritageChatContext, heritageScope: string) {
  const [messages, setMessages] = useState<ChatOverlayMessage[]>(() => [welcome()]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [restoring, setRestoring] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const activeRequest = useRef<AbortController | null>(null);
  const busy = useRef(false);
  const timeout = useRef<number | null>(null);
  const latestContext = useRef(context);
  latestContext.current = context;
  const accountId = chatAccountId(accessToken);
  const storageKey = chatStorageKey(heritageScope, accountId);
  const heritageId = context.heritage_id ?? null;

  useEffect(() => {
    const controller = new AbortController();
    if (!accessToken) {
      const history = rememberedGuestMessages(browserChatStorage("sessionStorage"), storageKey);
      setMessages([welcome(), ...history]);
      setRestoring(false);
      return;
    }
    const storage = browserChatStorage("localStorage");
    const id = accountId ? rememberedConversation(storage, storageKey) : null;
    if (!id || !accountId) { setRestoring(false); return; }
    activeRequest.current = controller;
    busy.current = true;
    setConversationId(id);
    timeout.current = window.setTimeout(() => controller.abort("timeout"), 15000);
    void getHeritageConversation(id, accountId, heritageId, accessToken, controller.signal).then((history) => {
      if (!controller.signal.aborted) setMessages([welcome(), ...history]);
    }).catch((failure: unknown) => {
      if (controller.signal.aborted && controller.signal.reason !== "timeout") return;
      if (failure instanceof ChatApiError && [401, 403, 404, 422].includes(failure.status)) {
        forgetChat(storage, storageKey);
        setConversationId(null);
      }
      setError(`Không tải được lịch sử. ${chatErrorMessage(failure)}`);
    }).finally(() => {
      if (activeRequest.current === controller) {
        if (timeout.current !== null) window.clearTimeout(timeout.current);
        timeout.current = null;
        activeRequest.current = null;
        busy.current = false;
        setRestoring(false);
      }
    });
    return () => {
      controller.abort();
      if (activeRequest.current === controller) {
        activeRequest.current = null;
        if (timeout.current !== null) window.clearTimeout(timeout.current);
        timeout.current = null;
      }
    };
  }, [accessToken, accountId, storageKey, heritageId]);

  useEffect(() => {
    if (!accessToken && !restoring && !sending) {
      rememberGuestMessages(browserChatStorage("sessionStorage"), storageKey, messages);
    }
  }, [accessToken, restoring, sending, storageKey, messages]);

  useEffect(() => () => {
    activeRequest.current?.abort();
    if (timeout.current !== null) window.clearTimeout(timeout.current);
  }, []);

  const send = useCallback(async (text?: string) => {
    const message = (text ?? input).trim();
    if (!message || busy.current || restoring) return;
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
      const response = await sendHeritageChatMessage(message, conversationId, latestContext.current,
        messages, accessToken, controller.signal);
      if (controller.signal.aborted) return;
      setConversationId(accessToken ? response.conversation_id : null);
      if (accessToken && accountId) rememberConversation(browserChatStorage("localStorage"), storageKey, response.conversation_id);
      setMessages((previous) => [...previous, {
        id: response.message_id, role: "assistant", content: response.answer,
        createdAt: new Date().toISOString(), citations: response.citations,
        needsUserChoice: response.needs_user_choice, abstained: response.abstained,
        answerType: response.answer_type, suggestions: overlaySuggestions(response.suggestions),
      }]);
    } catch (failure) {
      if (controller.signal.aborted && controller.signal.reason !== "timeout") return;
      setMessages((previous) => previous.filter((item) => item.id !== userMessage.id));
      setInput((draft) => draft || message);
      setError(controller.signal.reason === "timeout"
        ? "AI phản hồi quá thời gian. Vui lòng thử lại."
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
  }, [accessToken, accountId, conversationId, input, messages, restoring, storageKey]);

  const newConversation = useCallback(() => {
    activeRequest.current?.abort();
    activeRequest.current = null;
    if (timeout.current !== null) window.clearTimeout(timeout.current);
    timeout.current = null;
    busy.current = false;
    setSending(false);
    setRestoring(false);
    forgetChat(browserChatStorage(accessToken ? "localStorage" : "sessionStorage"), storageKey);
    setMessages([welcome()]);
    setConversationId(null);
    setInput("");
    setError(null);
  }, [accessToken, storageKey]);

  return { messages, input, setInput, sending, restoring, error, send, newConversation };
}
