"use client";

import { ArrowUpOutlined, BulbOutlined, LoadingOutlined } from "@ant-design/icons";
import { useEffect, useRef } from "react";
import { OVERLAY_QUICK_SUGGESTIONS } from "@/features/chat/config";
import styles from "@/features/chat/chat-overlay.module.css";

interface ChatInputBarProps {
  value: string;
  sending: boolean;
  disabled?: boolean;
  showSuggestions?: boolean;
  onChange: (value: string) => void;
  onSend: (text?: string) => void;
}

export function ChatInputBar({ value, sending, disabled = false, showSuggestions = true, onChange, onSend }: ChatInputBarProps) {
  const input = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { input.current?.focus(); }, []);
  useEffect(() => {
    const resize = () => {
      const field = input.current;
      if (!field) return;
      const computed = window.getComputedStyle(field);
      const maximum = (Number.parseFloat(computed.lineHeight) || 18) * 4
        + Number.parseFloat(computed.paddingTop) + Number.parseFloat(computed.paddingBottom);
      field.style.height = "auto";
      field.style.maxHeight = `${maximum}px`;
      field.style.height = `${Math.min(field.scrollHeight, maximum)}px`;
      field.style.overflowY = field.scrollHeight > maximum ? "auto" : "hidden";
    };
    resize();
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
  }, [value]);

  return (
    <form className={styles.composer} onSubmit={(event) => {
      event.preventDefault();
      if (value.trim() && !sending && !disabled) onSend();
    }}>
      {showSuggestions && <div className={`${styles.suggestions} ${styles.quickSuggestions}`} aria-label="Câu hỏi gợi ý">
        {OVERLAY_QUICK_SUGGESTIONS.map((suggestion) => (
          <button key={suggestion.label} type="button" disabled={sending || disabled} onClick={() => onSend(suggestion.value)}>
            {suggestion.label}
          </button>
        ))}
      </div>}
      <div className={styles.inputRow}>
        <BulbOutlined className={styles.inputIcon} aria-hidden="true" />
        <textarea ref={input} value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)}
          placeholder="Ask Mila anything…" aria-label="Message the heritage assistant" rows={1} maxLength={8000}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              if (value.trim() && !sending && !disabled) onSend();
            }
          }} />
        <button className={styles.sendButton} type="submit" disabled={!value.trim() || sending || disabled}
          aria-label={sending ? "Waiting for the assistant" : "Send message"}>
          {sending ? <LoadingOutlined spin /> : <ArrowUpOutlined />}
        </button>
      </div>
      <p className={styles.disclaimer}>Mila can make mistakes. Check the sources.</p>
    </form>
  );
}
