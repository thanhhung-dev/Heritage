"use client";

import { useEffect, useRef } from "react";
import { MilaAvatar } from "@/features/chat/components/ChatToggleButton";
import type { ChatOverlayMessage } from "@/features/chat/types/chatOverlay";
import styles from "@/features/chat/chat-overlay.module.css";

function sourceUrl(value: string | null) {
  try {
    const url = new URL(value ?? "");
    return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}

interface ChatMessageListProps {
  messages: ChatOverlayMessage[];
  sending: boolean;
  onSend: (text?: string) => void;
}

export function ChatMessageList({ messages, sending, onSend }: ChatMessageListProps) {
  const scroll = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight;
  }, [messages, sending]);

  return (
    <div ref={scroll} className={styles.messages} role="log" aria-live="polite" aria-relevant="additions text"
      aria-label="Conversation with Mila">
      {messages.map((message) => (
        <article key={message.id} className={`${styles.message} ${message.role === "user" ? styles.userMessage : ""}`}>
          {message.role === "assistant" && <MilaAvatar small />}
          <div className={styles.messageBody}>
            <p className={styles.messageText}>{message.content}</p>
            {message.suggestions?.length ? (
              <div className={styles.suggestions}>
                {message.suggestions.map((item) => (
                  <button key={item.value} type="button" disabled={sending} onClick={() => onSend(item.value)}>
                    {item.label}
                  </button>
                ))}
              </div>
            ) : null}
            {message.citations.length > 0 && (
              <details className={styles.citations}>
                <summary>Sources · {message.citations.length}</summary>
                <ol>{message.citations.map((citation) => {
                  const url = sourceUrl(citation.source_url);
                  return <li key={citation.id}>{url
                    ? <a href={url} target="_blank" rel="noopener noreferrer">{citation.source_title}</a>
                    : <span>{citation.source_title}</span>}</li>;
                })}</ol>
              </details>
            )}
            <time className={styles.timestamp} dateTime={message.createdAt}>
              {new Date(message.createdAt).toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit" })}
            </time>
          </div>
        </article>
      ))}
      {sending && (
        <div className={styles.message} role="status" aria-label="Mila is thinking">
          <MilaAvatar small />
          <span className={styles.thinking} aria-hidden="true"><i /><i /><i /></span>
        </div>
      )}
    </div>
  );
}
