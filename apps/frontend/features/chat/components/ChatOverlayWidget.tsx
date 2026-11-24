"use client";

import { CloseOutlined, CompressOutlined, ExpandAltOutlined, ReloadOutlined } from "@ant-design/icons";
import { useEffect, useId, useRef, useState, useSyncExternalStore } from "react";
import { ChatInputBar } from "@/features/chat/components/ChatInputBar";
import { ChatMessageList } from "@/features/chat/components/ChatMessageList";
import { ChatToggleButton } from "@/features/chat/components/ChatToggleButton";
import type { ChatOverlayMessage, ChatOverlayWidgetState } from "@/features/chat/types/chatOverlay";
import styles from "@/features/chat/chat-overlay.module.css";
import { useOverlayDrag } from "@/features/chat/useOverlayDrag";

interface ChatOverlayWidgetProps {
  messages: ChatOverlayMessage[];
  input: string;
  sending: boolean;
  disabled?: boolean;
  areaLabel?: string;
  sceneLabel?: string;
  suggestions?: readonly { label: string; value: string }[];
  error: string | null;
  onInputChange: (value: string) => void;
  onSend: (text?: string) => void;
  onNewConversation: () => void;
}

function HeritageSparkleLogo() {
  return (
    <svg width="36" height="36" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <path
        d="M14 2C14.6 8.2 19.8 13.4 26 14C19.8 14.6 14.6 19.8 14 26C13.4 19.8 8.2 14.6 2 14C8.2 13.4 13.4 8.2 14 2Z"
        fill="url(#heritage-sparkle-grad)"
      />
      <defs>
        <linearGradient id="heritage-sparkle-grad" x1="2" y1="2" x2="26" y2="26" gradientUnits="userSpaceOnUse">
          <stop stopColor="#FFD28A" />
          <stop offset="0.5" stopColor="#FFAD42" />
          <stop offset="1" stopColor="#FA500F" />
        </linearGradient>
      </defs>
    </svg>
  );
}

function subscribeToNetwork(onChange: () => void) {
  window.addEventListener("online", onChange);
  window.addEventListener("offline", onChange);
  return () => {
    window.removeEventListener("online", onChange);
    window.removeEventListener("offline", onChange);
  };
}

export function ChatOverlayWidget(props: ChatOverlayWidgetProps) {
  const panelId = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLElement>(null);
  const [mode, setMode] = useState<ChatOverlayWidgetState["mode"]>("closed");
  const [justClosed, setJustClosed] = useState(false);
  const [openCount, setOpenCount] = useState(0);
  const isOpen = mode !== "closed";
  const hasConversation = props.messages.some((message) => message.role === "user");
  const panelDrag = useOverlayDrag(panel, { enabled: isOpen, ignoreInteractive: true, layoutKey: mode });
  const online = useSyncExternalStore(subscribeToNetwork, () => navigator.onLine, () => true);

  useEffect(() => {
    if (typeof window !== "undefined" && "CSS" in window && "registerProperty" in window.CSS) {
      try {
        window.CSS.registerProperty({
          name: "--mask-angle",
          syntax: "<angle>",
          inherits: false,
          initialValue: "180deg",
        });
      } catch {
        // Already registered
      }
    }
  }, []);

  useEffect(() => {
    if (!panel.current) return;
    panel.current.inert = !isOpen;
    if (isOpen) panel.current.querySelector("textarea")?.focus();
  }, [isOpen]);
  const close = () => {
    setJustClosed(true);
    setMode("closed");
    requestAnimationFrame(() => trigger.current?.focus());
  };
  const open = () => {
    setJustClosed(false);
    setOpenCount((c) => c + 1);
    setMode("open");
  };

  return (
    <div className={styles.dock} data-chat-overlay onPointerDown={(event) => event.stopPropagation()}
      onWheel={(event) => event.stopPropagation()} onKeyDown={(event) => {
        event.stopPropagation();
        if (event.key === "Escape" && mode !== "closed") { event.preventDefault(); close(); }
      }}>
      <span id={`${panelId}-drag-help`} className={styles.dragHint}>
        Kéo thanh tiêu đề để di chuyển cửa sổ chat. Dùng phím mũi tên khi được chọn; giữ Shift để di chuyển nhanh hơn.
      </span>
      <ChatToggleButton panelId={panelId} open={isOpen} bouncing={justClosed} online={online} buttonRef={trigger}
        onClick={() => isOpen ? close() : open()} />
        <section ref={panel} id={panelId} data-chat-panel data-open={isOpen}
          data-chat-phase={props.sending ? "thinking" : hasConversation ? "conversation" : "welcome"}
          style={panelDrag.style} data-positioned={Boolean(panelDrag.position)} data-dragging={panelDrag.dragging}
          className={`${styles.panel} ${mode === "expanded" ? styles.panelExpanded : ""}`}
          role="dialog" aria-modal={false} aria-hidden={!isOpen}
          aria-label={["Heritage AI assistant", props.areaLabel, props.sceneLabel].filter(Boolean).join(" · ")}>
          <div
            key={openCount}
            className={`${styles.luminousGradient} ${
              !isOpen || hasConversation ? styles.luminousHidden : styles.luminousOpen
            }`}
            aria-hidden="true"
          >
            <div className={styles.energyWrapper}>
              <div className={`${styles.energyRing} ${styles.outerRing}`} />
              <div className={`${styles.energyRing} ${styles.innerRing}`} />
            </div>
          </div>
          <header className={styles.header} {...panelDrag.handlers} data-chat-drag-handle tabIndex={isOpen ? 0 : -1}
            role="group" aria-label="Di chuyển cửa sổ chat" aria-describedby={`${panelId}-drag-help`}
            title="Kéo để di chuyển cửa sổ chat">
            <div className={styles.headerConversationTitle}>
              {hasConversation ? (props.messages.find((m) => m.role === "user")?.content ?? "") : ""}
            </div>
            <div className={styles.headerActions}>
              <div className={styles.profilePill} title={props.areaLabel ?? "Heritage AI"}>
                <span className={styles.profilePillLabel}>{props.areaLabel ?? "Heritage"}</span>
                <span className={styles.profileAvatar} aria-hidden="true">H</span>
              </div>
              <button type="button" onClick={props.onNewConversation} aria-label="Start a new conversation" title="Cuộc trò chuyện mới">
                <ReloadOutlined />
              </button>
              <button type="button" aria-label={mode === "expanded" ? "Restore chat size" : "Expand chat"}
                title={mode === "expanded" ? "Thu nhỏ" : "Mở rộng"}
                aria-pressed={mode === "expanded"} onClick={() => setMode(mode === "expanded" ? "open" : "expanded")}>
                {mode === "expanded" ? <CompressOutlined /> : <ExpandAltOutlined />}
              </button>
              <button type="button" onClick={close} aria-label="Close assistant" title="Đóng"><CloseOutlined /></button>
            </div>
          </header>
          {!hasConversation && !props.sending ? (
            <div key={`zero-${openCount}`} className={styles.zeroState}>
              <div className={styles.zeroLogo}>
                <HeritageSparkleLogo />
              </div>
              <h2 className={styles.zeroGreeting}>Bạn muốn khám phá điều gì về di sản này?</h2>
            </div>
          ) : (
            <div className={styles.chatListFade}>
              <ChatMessageList messages={props.messages} sending={props.sending} onSend={props.onSend}
                hideWelcome />
            </div>
          )}
          {props.error && <p className={styles.error} role="alert">{props.error}</p>}
          <ChatInputBar value={props.input} sending={props.sending} disabled={props.disabled}
            contextLabel={props.sceneLabel}
            suggestions={props.suggestions}
            showSuggestions={!hasConversation && !props.sending && !props.disabled}
            onChange={props.onInputChange} onSend={props.onSend} />
        </section>
    </div>
  );
}
