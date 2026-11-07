"use client";

import { useEffect, useMemo, useState } from "react";

import { useHeritageTour } from "@/context/heritage-tour";
import { AUTH_CHANGE_EVENT } from "@/lib/auth";
import { resolveTourArea } from "@/lib/tour-chat-scope";
import { buildSceneChatSuggestions } from "@/lib/scene-chat-suggestions";
import { ChatOverlayWidget } from "@/features/chat/components/ChatOverlayWidget";
import type { ChatOverlayMessage } from "@/features/chat/types/chatOverlay";
import { getConversationAccountId, useConversationSession } from "@/hooks/useConversationSession";
import type { Message } from "./types";

const WELCOME_MESSAGE_ID = "mila-welcome";
const WELCOME_MESSAGE = "Bạn muốn khám phá điều gì về di sản này?";

function createWelcomeMessage(): Message {
  return {
    id: WELCOME_MESSAGE_ID,
    role: "assistant",
    content: WELCOME_MESSAGE,
    createdAt: new Date().toISOString(),
  };
}

function initialTourMessages(): Message[] { return [createWelcomeMessage()]; }

export function TourChatWidget() {
  const { payload, heritageSlug } = useHeritageTour();
  const [accountId, setAccountId] = useState(getConversationAccountId);

  useEffect(() => {
    const updateAccount = () => setAccountId(getConversationAccountId());
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
  const chat = useConversationSession({
    scope: `tour:${payload.heritage.id}:${area?.id ?? heritageSlug}`,
    initialMessages: initialTourMessages,
    disabled: !area,
    context: {
      active_area_id: area?.id,
      ...(Number.isInteger(payload.heritage.id) && payload.heritage.id > 0 ? { heritage_id: payload.heritage.id } : {}),
      heritage_context: {
        id: payload.heritage.id, slug: heritageSlug, title: payload.heritage.title, region: payload.heritage.region,
      },
      scene_context: currentScene ? {
        id: currentScene.id, key: currentSceneKey, slug: currentScene.slug,
        title: currentScene.title, description: currentScene.description?.slice(0, 1000) ?? null,
        sequence: currentScene.sequence,
      } : null,
    },
  });
  const sceneSuggestions = useMemo(
    () => buildSceneChatSuggestions(area, currentScene, currentSceneKey),
    [area, currentScene, currentSceneKey],
  );

  const overlayMessages = useMemo<ChatOverlayMessage[]>(() => chat.messages.map((message) => ({
    id: message.id, role: message.role, content: message.content,
    createdAt: message.createdAt ?? new Date(0).toISOString(),
  })), [chat.messages]);

  return <ChatOverlayWidget
    messages={overlayMessages} input={chat.input} sending={chat.sending} restoring={chat.restoring} disabled={!area}
    areaLabel={area?.title}
    sceneLabel={sceneSuggestions.contextLabel ?? undefined}
    suggestions={sceneSuggestions.suggestions}
    error={area ? chat.error : "Tour này chưa có khu vực hướng dẫn được xác nhận. Chat tạm khóa để tránh trả lời sai phạm vi."}
    onInputChange={chat.setInput} onSend={(text) => void chat.send(text)} onNewConversation={chat.startNewConversation}
  />;
}
