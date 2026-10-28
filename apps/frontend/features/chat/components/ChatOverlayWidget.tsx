"use client";

import { CloseOutlined, CompressOutlined, ExpandAltOutlined, ReloadOutlined } from "@ant-design/icons";
import { useId, useRef, useState } from "react";
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
  onInputChange: (value: string) => void;
  onSend: (text?: string) => void;
  onNewConversation: () => void;
}

export function ChatOverlayWidget(props: ChatOverlayWidgetProps) {
  const panelId = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const [mode, setMode] = useState<ChatOverlayWidgetState["mode"]>("closed");
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
      {mode === "closed" ? (
        <ChatToggleButton panelId={panelId} buttonRef={trigger} onClick={() => setMode("open")} />
      ) : (
        <section id={panelId} className={`${styles.panel} ${mode === "expanded" ? styles.panelExpanded : ""}`}
          role="dialog" aria-modal={false} aria-labelledby={`${panelId}-title`}>
          <header className={styles.header}>
            <MilaAvatar />
            <div className={styles.identity}>
              <h2 id={`${panelId}-title`}>Mila</h2>
              <p><span className={styles.statusDot} />AI Heritage Assistant</p>
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
          <span className={styles.contextLabel} title={props.contextLabel}>{props.contextLabel}</span>
          <ChatMessageList messages={props.messages} sending={props.sending} onSend={props.onSend} />
          {props.error && <p className={styles.error} role="alert">{props.error}</p>}
          <ChatInputBar value={props.input} sending={props.sending} onChange={props.onInputChange} onSend={props.onSend} />
        </section>
      )}
    </div>
  );
}
