"use client";

import { CloseOutlined } from "@ant-design/icons";
import { XProvider } from "@ant-design/x";
import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";

import { HeritageLogoMini } from "@/components/Logo/HeritageLogoMinimal";
import { useHeritageTour } from "@/context/heritage-tour";
import { getAccessToken, getUser } from "@/lib/auth";
import type { Message } from "./types";
import ChatInput from "./components/ChatInput";
import { ChatView } from "./components/ChatView";
import { SuggestionList } from "./components/SuggestionList";
import {
  buildSceneConversationContext,
  sendSceneChatMessage,
  type SceneChatRequest,
} from "./scene-chat-service";
import { useHeritageTheme } from "./useHeritageTheme";
import styles from "./tour-chat-widget.module.css";

const SCENE_SUGGESTIONS = [
  "Giới thiệu về cảnh này",
  "Địa điểm này có ý nghĩa văn hóa gì?",
  "Nên chú ý chi tiết nào trong cảnh?",
];

function createMessageId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

export function TourChatWidget() {
  const { payload, heritageSlug, currentSceneKey, currentScene } = useHeritageTour();
  const theme = useHeritageTheme();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [conversationOwnerId, setConversationOwnerId] = useState<string | null>(null);
  const panelId = useId();
  const titleId = useId();
  const launcherRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const requestRef = useRef<AbortController | null>(null);
  const previousHeritageRef = useRef(`${payload.heritage.id}:${heritageSlug}`);
  const shouldReturnFocusRef = useRef(false);

  const heritageTitle = payload.heritage.title;
  const sceneTitle = currentScene?.title ?? "Cảnh trong tour";

  useEffect(() => {
    const heritageIdentity = `${payload.heritage.id}:${heritageSlug}`;
    if (previousHeritageRef.current === heritageIdentity) return;

    previousHeritageRef.current = heritageIdentity;
    requestRef.current?.abort();
    requestRef.current = null;
    setMessages([]);
    setInput("");
    setLoading(false);
    setConversationId(null);
    setConversationOwnerId(null);
  }, [heritageSlug, payload.heritage.id]);

  useEffect(() => {
    if (isOpen) {
      closeRef.current?.focus();
      shouldReturnFocusRef.current = true;
      return;
    }

    if (shouldReturnFocusRef.current) {
      launcherRef.current?.focus();
      shouldReturnFocusRef.current = false;
    }
  }, [isOpen]);

  const closePanel = useCallback(() => setIsOpen(false), []);

  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closePanel();
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [closePanel, isOpen]);

  const send = useCallback(
    async (text?: string) => {
      const userMessage = (text ?? input).trim();
      if (!userMessage || loading) return;

      const accessToken = getAccessToken();
      const accountId = accessToken ? getUser()?.account_id ?? null : null;
      const switchedAccount =
        Boolean(accountId && conversationOwnerId && accountId !== conversationOwnerId);
      const history = switchedAccount ? [] : messages;
      const activeConversationId =
        accountId && conversationOwnerId === accountId ? conversationId : null;
      const userEntry: Message = {
        id: createMessageId(),
        role: "user",
        content: userMessage,
      };

      if (switchedAccount) {
        setMessages([]);
        setConversationId(null);
        setConversationOwnerId(null);
      }
      setMessages([...history, userEntry]);
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
        const currentAccountId = getAccessToken() ? getUser()?.account_id ?? null : null;
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

  const suggestions = useMemo(() => [...SCENE_SUGGESTIONS], []);

  useEffect(
    () => {
      return () => requestRef.current?.abort();
    },
    [],
  );

  return (
    <XProvider theme={theme}>
      <div className={styles.widget}>
        <button
          ref={launcherRef}
          type="button"
          className={`${styles.launcher} ${isOpen ? styles.launcherHidden : ""}`}
          aria-label={`Mở chat về ${heritageTitle}`}
          aria-expanded={isOpen}
          aria-controls={panelId}
          aria-hidden={isOpen}
          tabIndex={isOpen ? -1 : 0}
          onClick={() => setIsOpen(true)}
        >
          <span className={styles.launcherLogo} aria-hidden="true">
            <HeritageLogoMini size={40} radius={0} />
          </span>
          <span className={styles.launcherLabel}>Hỏi về di sản này</span>
        </button>

        <section
          id={panelId}
          className={`${styles.panel} ${isOpen ? styles.panelOpen : ""}`}
          role="dialog"
          aria-modal="false"
          aria-labelledby={titleId}
          aria-hidden={!isOpen}
          data-open={isOpen}
        >
          <header className={styles.header}>
            <div className={styles.identity}>
              <span className={styles.avatar} aria-hidden="true">
                <HeritageLogoMini size={30} />
              </span>
              <div className={styles.identityText}>
                <h2 id={titleId} className={styles.title}>Heritage Guide</h2>
                <span className={styles.assistantStatus}>
                  <span className={styles.statusIndicator} aria-hidden="true" />
                  Trợ lý di sản
                </span>
              </div>
            </div>
            <button
              ref={closeRef}
              type="button"
              className={styles.closeButton}
              aria-label="Đóng khung chat"
              onClick={closePanel}
            >
              <CloseOutlined aria-hidden="true" />
            </button>
            <p className={styles.sceneContext} aria-live="polite">
              <span>{heritageTitle}</span>
              <span className={styles.contextDivider} aria-hidden="true">·</span>
              <span>{sceneTitle}</span>
            </p>
          </header>

          {messages.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyAvatar} aria-hidden="true">
                <HeritageLogoMini size={42} />
              </div>
              <div className={styles.emptyCopy}>
                <h3>Bạn muốn tìm hiểu điều gì?</h3>
                <p>Hỏi về {sceneTitle.toLocaleLowerCase()} hoặc câu chuyện của địa điểm này.</p>
              </div>
              <div className={styles.emptyInput}>
                <ChatInput
                  value={input}
                  onChange={setInput}
                  onSubmit={() => void send()}
                  placeholder="Hỏi về cảnh này…"
                  loading={loading}
                  allowAttachments={false}
                />
              </div>
              <SuggestionList
                suggestions={suggestions}
                onSelect={(suggestion) => void send(suggestion)}
                compact
              />
            </div>
          ) : (
            <ChatView
              messages={messages}
              input={input}
              loading={loading}
              onInputChange={setInput}
              onSend={() => void send()}
              compact
            />
          )}
        </section>
      </div>
    </XProvider>
  );
}
