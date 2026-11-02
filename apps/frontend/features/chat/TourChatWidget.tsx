"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { useHeritageTour } from "@/context/heritage-tour";
import { AUTH_CHANGE_EVENT, getAccessToken, getUser } from "@/lib/auth";
import { ChatOverlayWidget } from "@/features/chat/components/ChatOverlayWidget";
import type { ChatOverlayMessage } from "@/features/chat/types/chatOverlay";
import type { Message } from "./types";
import {
  buildSceneConversationContext,
  sendSceneChatMessage,
  type SceneChatRequest,
} from "./scene-chat-service";

const WELCOME_MESSAGE_ID = "mila-welcome";
const WELCOME_MESSAGE =
  "Hi, I’m Mila, your AI heritage guide. What would you like to discover?";

function createMessageId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

function createWelcomeMessage(): Message {
  return {
    id: WELCOME_MESSAGE_ID,
    role: "assistant",
    content: WELCOME_MESSAGE,
    createdAt: new Date().toISOString(),
  };
}

function getCurrentAccountId(): string | null {
  return getAccessToken() ? getUser()?.account_id ?? null : null;
}

export function TourChatWidget() {
  const { payload, heritageSlug, currentSceneKey, currentScene } = useHeritageTour();
  const [messages, setMessages] = useState<Message[]>(() => [createWelcomeMessage()]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversationOwnerId, setConversationOwnerId] = useState<string | null>(null);
  const requestRef = useRef<AbortController | null>(null);
  const previousHeritageRef = useRef(`${payload.heritage.id}:${heritageSlug}`);
  const previousAccountRef = useRef(getCurrentAccountId());

  const heritageTitle = payload.heritage.title;
  const sceneTitle = currentScene?.title ?? "Cảnh trong tour";

  useEffect(() => {
    const heritageIdentity = `${payload.heritage.id}:${heritageSlug}`;
    if (previousHeritageRef.current === heritageIdentity) return;

    previousHeritageRef.current = heritageIdentity;
    requestRef.current?.abort();
    requestRef.current = null;
    setMessages([createWelcomeMessage()]);
    setInput("");
    setLoading(false);
    setConversationId(null);
    setConversationOwnerId(null);
  }, [heritageSlug, payload.heritage.id]);

  useEffect(() => {
    const handleAuthChange = () => {
      const accountId = getCurrentAccountId();
      if (previousAccountRef.current === accountId) return;

      previousAccountRef.current = accountId;
      requestRef.current?.abort();
      requestRef.current = null;
      setMessages([createWelcomeMessage()]);
      setInput("");
      setLoading(false);
      setConversationId(null);
      setConversationOwnerId(null);
    };

    window.addEventListener(AUTH_CHANGE_EVENT, handleAuthChange);
    return () => window.removeEventListener(AUTH_CHANGE_EVENT, handleAuthChange);
  }, []);

  const startNewConversation = useCallback(() => {
    requestRef.current?.abort();
    requestRef.current = null;
    setMessages([createWelcomeMessage()]);
    setInput("");
    setLoading(false);
    setConversationId(null);
    setConversationOwnerId(null);
  }, []);

  const send = useCallback(
    async (text?: string) => {
      const userMessage = (text ?? input).trim();
      if (!userMessage || loading) return;

      const accountId = getCurrentAccountId();
      const switchedAccount =
        Boolean(accountId && conversationOwnerId && accountId !== conversationOwnerId);
      const displayHistory = switchedAccount ? [createWelcomeMessage()] : messages;
      const history = displayHistory.filter(
        (message) => message.id !== WELCOME_MESSAGE_ID,
      );
      const activeConversationId =
        accountId && conversationOwnerId === accountId ? conversationId : null;
      const userEntry: Message = {
        id: createMessageId(),
        role: "user",
        content: userMessage,
        createdAt: new Date().toISOString(),
      };

      if (switchedAccount) {
        setConversationId(null);
        setConversationOwnerId(null);
      }
      setMessages([...displayHistory, userEntry]);
      setInput("");
      setLoading(true);

      const controller = new AbortController();
      requestRef.current?.abort();
      requestRef.current = controller;

      const heritageId = payload.heritage.id;
      const request: SceneChatRequest = {
        message: userMessage,
        ...(Number.isInteger(heritageId) && heritageId > 0
          ? { heritage_id: heritageId }
          : {}),
        heritage_context: {
          id: heritageId,
          slug: heritageSlug,
          title: heritageTitle,
          region: payload.heritage.region,
        },
        scene_context: currentScene
          ? {
              id: currentScene.id,
              key: currentSceneKey,
              slug: currentScene.slug,
              title: currentScene.title,
              description: currentScene.description,
              sequence: currentScene.sequence,
            }
          : null,
        ...(activeConversationId
          ? { conversation_id: activeConversationId }
          : { conversation_context: buildSceneConversationContext(history) }),
      };

      try {
        const response = await sendSceneChatMessage(request, controller.signal);
        if (controller.signal.aborted) return;

        const currentAccountId = getCurrentAccountId();
        if (currentAccountId !== accountId) return;

        if (accountId && currentAccountId === accountId) {
          setConversationId(response.conversationId);
          setConversationOwnerId(accountId);
        } else {
          setConversationId(null);
          setConversationOwnerId(null);
        }

        setMessages((currentMessages) => [
          ...currentMessages,
          {
            id: createMessageId(),
            role: "assistant",
            content: response.answer,
            createdAt: new Date().toISOString(),
            sources: response.sources,
            correctedFrom: response.correctedFrom,
            correctedTo: response.correctedTo,
          },
        ]);
      } catch (error) {
        if (controller.signal.aborted) return;

        setMessages((currentMessages) => [
          ...currentMessages,
          {
            id: createMessageId(),
            role: "assistant",
            createdAt: new Date().toISOString(),
            content:
              error instanceof Error
                ? error.message
                : "Không thể gửi câu hỏi lúc này. Vui lòng thử lại.",
          },
        ]);
      } finally {
        if (requestRef.current === controller) {
          requestRef.current = null;
          setLoading(false);
        }
      }
    },
    [
      conversationId,
      conversationOwnerId,
      currentScene,
      currentSceneKey,
      heritageSlug,
      heritageTitle,
      input,
      loading,
      messages,
      payload.heritage.id,
      payload.heritage.region,
    ],
  );

  const overlayMessages = useMemo<ChatOverlayMessage[]>(
    () =>
      messages.map((message) => ({
        id: message.id,
        role: message.role,
        content: message.content,
        createdAt: message.createdAt ?? new Date(0).toISOString(),
        citations: (message.sources ?? []).map((source, index) => ({
          id: `${message.id}-${source.chunk_id ?? index}`,
          message_id: message.id,
          source_title: source.doc ?? source.heading ?? "Nguồn tham khảo",
          source_url: source.url ?? null,
          relevance_score: null,
        })),
      })),
    [messages],
  );

  useEffect(
    () => {
      return () => requestRef.current?.abort();
    },
    [],
  );

  return (
    <ChatOverlayWidget
      messages={overlayMessages}
      input={input}
      sending={loading}
      error={null}
      contextLabel={sceneTitle}
      heritageName={heritageTitle}
      authenticated={Boolean(getAccessToken())}
      onInputChange={setInput}
      onSend={(text) => void send(text)}
      onNewConversation={startNewConversation}
    />
  );
}
