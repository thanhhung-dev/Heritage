"use client";

import { useEffect, useId, useRef, useState } from "react";
import { ChatMarkdown } from "@/features/chat/components/ChatMarkdown";
import { ChatActions } from "@/features/chat/components/ChatActions";
import { ChatProcessing } from "@/features/chat/components/ChatProcessing";
import type { Source } from "@/features/chat/types";
import type { ChatOverlayMessage } from "@/features/chat/types/chatOverlay";
import { safeSourceUrl } from "@/lib/safe-source-url";
import styles from "@/features/chat/chat-overlay.module.css";

interface ChatMessageListProps {
  messages: ChatOverlayMessage[];
  sending: boolean;
  onSend: (text?: string) => void;
  hideWelcome: boolean;
}

function SourceLink({ url, source }: { url: string; source: Source }) {
  const [iconFailed, setIconFailed] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const previewId = useId();
  const website = new URL(url);
  const hostname = website.hostname.replace(/^www\./, "");
  const title = source.doc?.trim() || source.heading?.trim() || hostname;
  const label = `${title} — ${hostname}${source.source_type === "web" ? " — Nguồn web chưa được thẩm định" : ""}`;

  return (
    <a className={styles.sourceLink} href={url} target="_blank" rel="noopener noreferrer"
      aria-label={`${label} (mở trong tab mới)`} aria-describedby={previewOpen ? previewId : undefined}
      onMouseEnter={() => setPreviewOpen(true)} onMouseLeave={() => setPreviewOpen(false)}
      onFocus={() => setPreviewOpen(true)} onBlur={() => setPreviewOpen(false)}
      onKeyDown={(event) => { if (event.key === "Escape") setPreviewOpen(false); }}>
      <span className={styles.sourceIcon} aria-hidden="true">
        <span className={styles.sourceInitial}>{hostname.charAt(0).toUpperCase()}</span>
        {!iconFailed && (
          // Favicons come directly from the cited website and need no image optimization.
          // eslint-disable-next-line @next/next/no-img-element
          <img className={styles.sourceFavicon} src={`${website.origin}/favicon.ico`} alt=""
            width={14} height={14} loading="lazy" referrerPolicy="no-referrer"
            onError={() => setIconFailed(true)} />
        )}
      </span>
      <span className={styles.sourceTitle}>{title}</span>
      {previewOpen && <span className={styles.sourcePreview} id={previewId} role="tooltip">
        <strong>{title}</strong>
        <span>{hostname}</span>
        {source.source_type === "web" && <span>Nguồn web chưa được thẩm định</span>}
      </span>}
    </a>
  );
}

function SourceLinks({ sources }: { sources: Source[] }) {
  const urls = new Set<string>();
  const links = sources.flatMap((source) => {
    if (source.source_type !== "web") return [];
    const url = safeSourceUrl(source.url);
    if (!url || urls.has(url)) return [];
    urls.add(url);
    return [{ url, source }];
  });

  if (!links.length) return null;
  return (
    <span className={styles.sourceLinks} role="group" aria-label="Nguồn của câu trả lời">
      {links.map(({ url, source }) => <SourceLink key={url} url={url} source={source} />)}
    </span>
  );
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
      {messages.map((message, messageIndex) => (
        <article key={message.id} aria-hidden={message.id === "mila-welcome" && hideWelcome}
          className={`${styles.message} ${message.role === "user" ? styles.userMessage : ""} ${message.id === "mila-welcome" ? styles.welcomeMessage : ""}`}>
          <div className={styles.messageBody}>
            {message.role === "user" && <time className={styles.timestamp} dateTime={message.createdAt}>
              {new Date(message.createdAt).toLocaleTimeString("vi", { hour: "2-digit", minute: "2-digit" })}
            </time>}
            {message.answerType === "development_mock" && <span className={styles.answerStatus}>Sample answer</span>}
            {message.needsUserChoice && <span className={styles.answerStatus}>Cần làm rõ đối tượng</span>}
            {message.abstained && message.answerType !== "out_of_scope"
              && message.answerType !== "insufficient_evidence" && (
              <span className={styles.answerStatus}>Chưa có câu trả lời được xác minh</span>
            )}
            <div className={styles.messageText}>
              {message.role === "assistant" ? (
                <ChatMarkdown content={message.content} animate={message.id !== "mila-welcome"}
                  trailing={message.sources?.length ? <SourceLinks sources={message.sources} /> : undefined} />
              ) : (
                <p>{message.content}</p>
              )}
            </div>
            {message.role === "assistant" && message.id !== "mila-welcome" && (
              <ChatActions content={message.content} />
            )}
            {message.role === "assistant" && messageIndex === messages.length - 1
              && !sending && message.suggestions?.length ? (
              <div className={styles.inlineFollowUp} role="group" aria-label="Khám phá tiếp">
                {message.suggestions.slice(0, 2).map((item) => (
                    <button
                      key={item.value}
                      type="button"
                      className={styles.inlineFollowUpLink}
                      disabled={sending}
                      onClick={() => onSend(item.value)}
                    >
                      {item.label}
                    </button>
                ))}
              </div>
            ) : null}
          </div>
        </article>
      ))}
      {sending && (
        <div className={styles.message}>
          <div className={styles.messageBody}>
            <ChatProcessing question={[...messages].reverse().find((message) => message.role === "user")?.content ?? ""} />
          </div>
        </div>
      )}
      <div ref={end} className={styles.scrollEnd} aria-hidden="true" />
    </div>
  );
}
