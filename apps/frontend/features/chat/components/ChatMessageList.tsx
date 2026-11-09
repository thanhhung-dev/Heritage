"use client";

import { useEffect, useRef } from "react";
import { ChatMarkdown } from "@/features/chat/components/ChatMarkdown";
import type { ChatOverlayMessage } from "@/features/chat/types/chatOverlay";
import { safeSourceUrl } from "@/lib/safe-source-url";
import styles from "@/features/chat/chat-overlay.module.css";

interface ChatMessageListProps {
  messages: ChatOverlayMessage[];
  sending: boolean;
  onSend: (text?: string) => void;
  hideWelcome: boolean;
}

export function ChatMessageList({ messages, sending, onSend, hideWelcome }: ChatMessageListProps) {
  const scroll = useRef<HTMLDivElement>(null);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView({ block: "nearest", behavior: "instant" });
  }, [messages, sending]);

  return (
    <div ref={scroll} className={styles.messages} role="log" aria-live="polite" aria-relevant="additions text"
      aria-label="Heritage AI conversation">
      {messages.map((message) => (
        <article key={message.id} aria-hidden={message.id === "mila-welcome" && hideWelcome}
          className={`${styles.message} ${message.role === "user" ? styles.userMessage : ""} ${message.id === "mila-welcome" ? styles.welcomeMessage : ""}`}>
          <div className={styles.messageBody}>
            {message.role === "user" && <time className={styles.timestamp} dateTime={message.createdAt}>
              {new Date(message.createdAt).toLocaleTimeString("vi", { hour: "2-digit", minute: "2-digit" })}
            </time>}
            {message.answerType === "development_mock" && <span className={styles.answerStatus}>Sample answer</span>}
            {message.replyContext && <span className={styles.answerStatus} data-reply-context>
              Về {message.replyContext.scene_key} · {message.replyContext.scene_title}
              {message.replyContext.highlight_title ? ` · ${message.replyContext.highlight_title}` : ""}
            </span>}
            {message.needsUserChoice && <span className={styles.answerStatus}>Cần làm rõ đối tượng</span>}
            {message.abstained && <span className={styles.answerStatus}>Chưa có câu trả lời được xác minh</span>}
            <div className={styles.messageText}>
              {message.role === "assistant" ? (
                <ChatMarkdown content={message.content} animate={message.id !== "mila-welcome"} />
              ) : (
                <p>{message.content}</p>
              )}
            </div>
            {message.role === "assistant" && !!message.sources?.length && <details className={styles.citations}>
              <summary>Nguồn tham khảo ({message.sources.length})</summary>
              <ol>{message.sources.map((source, index) => {
                const url = safeSourceUrl(source.url);
                return <li key={`${source.chunk_id ?? "source"}-${index}`}>
                  {url ? <a href={url} target="_blank" rel="noopener noreferrer">{source.doc ?? source.heading ?? `Nguồn ${index + 1}`}</a>
                    : source.doc ?? source.heading ?? `Đoạn nguồn ${source.chunk_id ?? index + 1}`}
                </li>;
              })}</ol>
            </details>}
            {message.suggestions?.length ? (
              <div className={styles.suggestions}>
                {message.suggestions.map((item) => (
                  <button key={item.value} type="button" disabled={sending} onClick={() => onSend(item.value)}>
                    {item.label}
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        </article>
      ))}
      {sending && (
        <div className={styles.message} role="status" aria-label="AI đang trả lời">
          <span className={styles.thinking} aria-hidden="true"><i /><i /><i /></span>
        </div>
      )}
      <div ref={end} className={styles.scrollEnd} aria-hidden="true" />
    </div>
  );
}
