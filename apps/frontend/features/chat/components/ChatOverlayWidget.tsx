"use client";

import { CloseOutlined, CompressOutlined, ExpandAltOutlined, ReloadOutlined } from "@ant-design/icons";
import { useEffect, useId, useRef, useState, useSyncExternalStore } from "react";
import { ChatInputBar } from "@/features/chat/components/ChatInputBar";
import { ChatMessageList } from "@/features/chat/components/ChatMessageList";
import { ChatToggleButton, MilaAvatar } from "@/features/chat/components/ChatToggleButton";
import type { ChatOverlayMessage, ChatOverlayWidgetState } from "@/features/chat/types/chatOverlay";
import styles from "@/features/chat/chat-overlay.module.css";

interface ChatOverlayWidgetProps {
  messages: ChatOverlayMessage[];
  input: string;
  sending: boolean;
  error: string | null;
  contextLabel: string;
  heritageName: string;
  authenticated: boolean;
  onInputChange: (value: string) => void;
  onSend: (text?: string) => void;
  onNewConversation: () => void;
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
  const isOpen = mode !== "closed";
  const online = useSyncExternalStore(subscribeToNetwork, () => navigator.onLine, () => true);
  useEffect(() => {
    if (!panel.current) return;
    panel.current.inert = !isOpen;
    if (isOpen) panel.current.querySelector("textarea")?.focus();
  }, [isOpen]);
  const close = () => {
    setMode("closed");
    requestAnimationFrame(() => trigger.current?.focus());
  };

  return (
    <div className={styles.dock} data-chat-overlay onPointerDown={(event) => event.stopPropagation()}
      onWheel={(event) => event.stopPropagation()} onKeyDown={(event) => {
        event.stopPropagation();
        if (event.key === "Escape" && mode !== "closed") { event.preventDefault(); close(); }
      }}>
      <ChatToggleButton panelId={panelId} open={isOpen} online={online} buttonRef={trigger}
        onClick={() => isOpen ? close() : setMode("open")} />
        <section ref={panel} id={panelId} data-chat-panel data-open={isOpen}
          className={`${styles.panel} ${mode === "expanded" ? styles.panelExpanded : ""}`}
          role="dialog" aria-modal={false} aria-hidden={!isOpen} aria-labelledby={`${panelId}-title`}>
          <header className={styles.header}>
            <MilaAvatar />
            <div className={styles.identity}>
              <h2 id={`${panelId}-title`} title="Heritage AI Assistant">Mila</h2>
              <p><span className={`${styles.statusDot} ${!online ? styles.statusOffline : ""}`}
                title={online ? "Trực tuyến" : "Ngoại tuyến"} />
                AI Heritage Assistant
              </p>
            </div>
            <div className={styles.headerActions}>
              <button type="button" onClick={props.onNewConversation} aria-label="Start a new conversation" title="New conversation">
                <ReloadOutlined />
              </button>
              <button type="button" aria-label={mode === "expanded" ? "Restore chat size" : "Expand chat"}
                aria-pressed={mode === "expanded"} onClick={() => setMode(mode === "expanded" ? "open" : "expanded")}>
                {mode === "expanded" ? <CompressOutlined /> : <ExpandAltOutlined />}
              </button>
              <button type="button" onClick={close} aria-label="Close assistant"><CloseOutlined /></button>
            </div>
          </header>
          <div className={styles.contextBadges}>
            <span className={styles.heritageBadge} title={props.heritageName}>{props.heritageName}</span>
            <span className={styles.visitorBadge}>{props.authenticated ? "Thành viên" : "Guest"}</span>
          </div>
          <span className={styles.contextLabel} title={props.contextLabel}>{props.contextLabel}</span>
          <ChatMessageList messages={props.messages} sending={props.sending} onSend={props.onSend} />
          {props.error && <p className={styles.error} role="alert">{props.error}</p>}
          <ChatInputBar value={props.input} sending={props.sending} onChange={props.onInputChange} onSend={props.onSend} />
        </section>
    </div>
  );
}
