"use client";

import { useEffect, useRef, useState } from "react";
import { MilaAvatar } from "@/features/chat/components/ChatToggleButton";
import { ChatMarkdown } from "@/features/chat/components/ChatMarkdown";
import type { ChatOverlayMessage } from "@/features/chat/types/chatOverlay";
import { safeSourceUrl } from "@/lib/safe-source-url";
import styles from "@/features/chat/chat-overlay.module.css";

interface ChatMessageListProps {
  messages: ChatOverlayMessage[];
  sending: boolean;
  onSend: (text?: string) => void;
}

export function ChatMessageList({ messages, sending, onSend }: ChatMessageListProps) {
  const scroll = useRef<HTMLDivElement>(null);
  const end = useRef<HTMLDivElement>(null);
  const [selectedCitation, setSelectedCitation] = useState<string | null>(null);
  useEffect(() => {
    end.current?.scrollIntoView({ block: "nearest", behavior: "instant" });
  }, [messages, sending]);

  return (
    <div ref={scroll} className={styles.messages} role="log" aria-live="polite" aria-relevant="additions text"
      aria-label="Heritage AI conversation">
      {messages.map((message) => (
        <article key={message.id} className={`${styles.message} ${message.role === "user" ? styles.userMessage : ""}`}>
          {message.role === "assistant" && <MilaAvatar small />}
          <div className={styles.messageBody}>
            {message.answerType === "development_mock" && <span className={styles.answerStatus}>Sample answer</span>}
            {message.needsUserChoice && <span className={styles.answerStatus}>Choose a heritage</span>}
            {message.abstained && <span className={styles.answerStatus}>No verified answer</span>}
            <div className={styles.messageText}>
              {message.role === "assistant" ? <ChatMarkdown content={message.content} /> : <p>{message.content}</p>}
            </div>
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
              <div className={styles.citations} aria-label="Nguồn tham khảo">
                <div className={styles.citationBadges}>{message.citations.map((citation, index) => (
                  <button type="button" key={citation.id} data-citation={citation.id}
                    aria-expanded={selectedCitation === citation.id} aria-controls={`source-${citation.id}`}
                    onClick={() => setSelectedCitation(selectedCitation === citation.id ? null : citation.id)}>
                    <span>{index + 1}</span>{citation.source_title}
                  </button>
                ))}</div>
                {message.citations.filter((item) => item.id === selectedCitation).map((citation) => {
                  const url = safeSourceUrl(citation.source_url);
                  return <div key={citation.id} id={`source-${citation.id}`} className={styles.citationPanel}
                    role="region" aria-label="Chi tiết nguồn tham khảo">
                    <strong>{citation.source_title}</strong>
                    {url ? <a href={url} target="_blank" rel="noopener noreferrer">Mở nguồn tham khảo ↗</a>
                      : <p>Nguồn này không có liên kết công khai.</p>}
                    {citation.relevance_score !== null && <p>Điểm liên quan: {citation.relevance_score.toFixed(2)}</p>}
                  </div>;
                })}
              </div>
            )}
            <time className={styles.timestamp} dateTime={message.createdAt}>
              {new Date(message.createdAt).toLocaleTimeString("en", { hour: "2-digit", minute: "2-digit" })}
            </time>
          </div>
        </article>
      ))}
      {sending && (
        <div className={styles.message} role="status" aria-label="AI đang trả lời">
          <MilaAvatar small />
          <span className={styles.thinking} aria-hidden="true"><i /><i /><i /></span>
        </div>
      )}
      <div ref={end} className={styles.scrollEnd} aria-hidden="true" />
    </div>
  );
}
