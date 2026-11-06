"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { useHeritageTour } from "@/context/heritage-tour";
import { AUTH_CHANGE_EVENT, getAccessToken, getUser } from "@/lib/auth";
import { resolveTourArea, tourQuestions } from "@/lib/tour-chat-scope.mjs";
import { ChatOverlayWidget } from "@/features/chat/components/ChatOverlayWidget";
import type { ChatOverlayMessage } from "@/features/chat/types/chatOverlay";
import { buildSceneConversationContext, sendSceneChatMessage, type SceneChatRequest } from "./scene-chat-service";
import type { Message } from "./types";

const WELCOME_MESSAGE_ID = "mila-welcome";

function createMessageId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

function createWelcomeMessage(title?: string): Message {
  return {
    id: WELCOME_MESSAGE_ID,
    role: "assistant",
    content: title
      ? `Mình đồng hành cùng bạn tại ${title}. Bạn muốn tìm hiểu lịch sử, kiến trúc hay những câu chuyện tại đây?`
      : "Hướng dẫn viên đang chờ cấu hình khu vực cho tour này.",
    createdAt: new Date().toISOString(),
  };
}

function getCurrentAccountId(): string | null {
  return getAccessToken() ? getUser()?.account_id ?? null : null;
}

export function TourChatWidget() {
  const { payload, heritageSlug } = useHeritageTour();
  const [accountId, setAccountId] = useState(getCurrentAccountId);

  useEffect(() => {
    const updateAccount = () => setAccountId(getCurrentAccountId());
    window.addEventListener(AUTH_CHANGE_EVENT, updateAccount);
    return () => window.removeEventListener(AUTH_CHANGE_EVENT, updateAccount);
  }, []);

  // A different tour/account gets a fresh component instance immediately. Old
  // callbacks can only update the unmounted instance, never the new tour state.
  return <AreaTourChat key={`${payload.heritage.id}:${heritageSlug}:${accountId ?? "guest"}`} />;
}

function AreaTourChat() {
  const { payload, heritageSlug, currentSceneKey, currentScene } = useHeritageTour();
  const area = resolveTourArea(heritageSlug);
  const [messages, setMessages] = useState<Message[]>(() => [createWelcomeMessage(area?.title)]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [questions, setQuestions] = useState<string[]>(() => area ? tourQuestions(area) : []);
  const requestRef = useRef<AbortController | null>(null);

  const startNewConversation = useCallback(() => {
    requestRef.current?.abort();
    requestRef.current = null;
    setMessages([createWelcomeMessage(area?.title)]);
    setQuestions(area ? tourQuestions(area) : []);
    setInput("");
    setError(null);
    setLoading(false);
  }, [area]);

  const send = useCallback(async (text?: string) => {
    const userMessage = (text ?? input).trim();
    if (!userMessage || !area || requestRef.current) return;

    const accountId = getCurrentAccountId();
    const history = messages.filter((message) => message.id !== WELCOME_MESSAGE_ID);
    const controller = new AbortController();
    requestRef.current = controller;
    setMessages((current) => [...current, {
      id: createMessageId(), role: "user", content: userMessage, createdAt: new Date().toISOString(),
    }]);
    setInput("");
    setError(null);
    setLoading(true);

    const heritageId = payload.heritage.id;
    const request: SceneChatRequest = {
      message: userMessage,
      active_area_id: area.id,
      ...(Number.isInteger(heritageId) && heritageId > 0 ? { heritage_id: heritageId } : {}),
      heritage_context: {
        id: heritageId, slug: heritageSlug, title: payload.heritage.title, region: payload.heritage.region,
      },
      scene_context: currentScene ? {
        id: currentScene.id, key: currentSceneKey, slug: currentScene.slug,
        title: currentScene.title, description: currentScene.description?.slice(0, 1000) ?? null,
        sequence: currentScene.sequence,
      } : null,
      // This branch's /api/chat is stateless. Keep bounded history in this tour
      // instance for both members and guests; never reuse another tour's ID.
      conversation_context: buildSceneConversationContext(history),
    };

    const isCurrent = () => !controller.signal.aborted
      && requestRef.current === controller && getCurrentAccountId() === accountId;
    try {
      const response = await sendSceneChatMessage(request, controller.signal);
      if (!isCurrent()) return;
      setQuestions(response.followUpQuestions);
      setMessages((current) => [...current, {
        id: createMessageId(), role: "assistant", content: response.answer,
        createdAt: new Date().toISOString(), sources: response.sources,
      }]);
    } catch (failure) {
      if (!isCurrent()) return;
      setError(failure instanceof Error ? failure.message : "Không thể gửi câu hỏi lúc này. Vui lòng thử lại.");
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null;
        setLoading(false);
      }
    }
  }, [area, currentScene, currentSceneKey, heritageSlug, input, messages, payload.heritage]);

  const overlayMessages = useMemo<ChatOverlayMessage[]>(() => messages.map((message) => ({
    id: message.id, role: message.role, content: message.content,
    createdAt: message.createdAt ?? new Date(0).toISOString(),
    citations: (message.sources ?? []).map((source, index) => ({
      id: `${message.id}-${source.chunk_id ?? index}`, message_id: message.id,
      source_title: source.doc ?? source.heading ?? "Nguồn tham khảo",
      source_url: source.url ?? null, relevance_score: null,
    })),
  })), [messages]);

  useEffect(() => () => requestRef.current?.abort(), []);

  return <ChatOverlayWidget
    messages={overlayMessages} input={input} sending={loading} disabled={!area}
    areaLabel={area?.title}
    suggestions={questions.map((question) => ({ label: question, value: question }))}
    error={area ? error : "Tour này chưa có khu vực hướng dẫn được xác nhận. Chat tạm khóa để tránh trả lời sai phạm vi."}
    onInputChange={setInput} onSend={(text) => void send(text)} onNewConversation={startNewConversation}
  />;
}