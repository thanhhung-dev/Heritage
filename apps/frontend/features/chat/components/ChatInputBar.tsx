"use client";

import { ArrowUpOutlined, BulbOutlined, LoadingOutlined } from "@ant-design/icons";
import { useEffect, useRef } from "react";
import styles from "@/features/chat/chat-overlay.module.css";

interface ChatInputBarProps {
  value: string;
  sending: boolean;
  onChange: (value: string) => void;
  onSend: (text?: string) => void;
}

export function ChatInputBar({ value, sending, onChange, onSend }: ChatInputBarProps) {
  const input = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { input.current?.focus(); }, []);
  useEffect(() => {
    if (!input.current) return;
    input.current.style.height = "auto";
    input.current.style.height = `${Math.min(input.current.scrollHeight, 100)}px`;
  }, [value]);

  return (
    <form className={styles.composer} onSubmit={(event) => {
      event.preventDefault();
      if (value.trim() && !sending) onSend();
    }}>
      <div className={styles.inputRow}>
        <BulbOutlined className={styles.inputIcon} aria-hidden="true" />
        <textarea ref={input} value={value} onChange={(event) => onChange(event.target.value)}
          placeholder="Ask Mila anything…" aria-label="Message the heritage assistant" rows={1} maxLength={8000}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              if (value.trim() && !sending) onSend();
            }
          }} />
        <button className={styles.sendButton} type="submit" disabled={!value.trim() || sending}
          aria-label={sending ? "Waiting for the assistant" : "Send message"}>
          {sending ? <LoadingOutlined spin /> : <ArrowUpOutlined />}
        </button>
      </div>
      <p className={styles.disclaimer}>Mila can make mistakes. Check the sources.</p>
    </form>
  );
}
