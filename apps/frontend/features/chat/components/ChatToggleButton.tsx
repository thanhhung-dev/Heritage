"use client";

import type { Ref } from "react";
import styles from "@/features/chat/chat-overlay.module.css";

export function MilaAvatar({ small = false }: { small?: boolean }) {
  return (
    <span className={`${styles.avatar} ${small ? styles.avatarSmall : ""}`} aria-hidden="true">
      <svg viewBox="0 0 32 32" fill="none">
        <path d="M7 26V14a9 9 0 0 1 18 0v12l-3-2-3 2-3-2-3 2-3-2-3 2Z" fill="#f5f2f9" />
        <ellipse cx="12.5" cy="15" rx="1.5" ry="2" fill="#a69ab7" />
        <ellipse cx="19.5" cy="15" rx="1.5" ry="2" fill="#a69ab7" />
        <path d="M14 20c1.3 1 2.7 1 4 0" stroke="#a69ab7" strokeLinecap="round" />
      </svg>
    </span>
  );
}

interface ChatToggleButtonProps {
  panelId: string;
  onClick: () => void;
  buttonRef?: Ref<HTMLButtonElement>;
}

export function ChatToggleButton({ panelId, onClick, buttonRef }: ChatToggleButtonProps) {
  return (
    <button ref={buttonRef} className={styles.toggle} type="button" onClick={onClick}
      aria-label="Open heritage AI assistant" aria-controls={panelId} aria-expanded={false}>
      <MilaAvatar small />
      <span>Ask AI</span>
    </button>
  );
}
