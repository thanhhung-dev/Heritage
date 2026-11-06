"use client";

import type { Ref } from "react";
import { CloseOutlined } from "@ant-design/icons";
import { BotAvatar } from "bot-avatars";
import styles from "@/features/chat/chat-overlay.module.css";

export function MilaAvatar() {
  return (
    <span className={styles.avatar} aria-hidden="true">
      <BotAvatar type="star" face="mouth" size={30} interactive={false} />
    </span>
  );
}

interface ChatToggleButtonProps {
  panelId: string;
  open: boolean;
  bouncing?: boolean;
  online: boolean;
  onClick: () => void;
  buttonRef?: Ref<HTMLButtonElement>;
}

export function ChatToggleButton({ panelId, open, bouncing = false, online, onClick, buttonRef }: ChatToggleButtonProps) {
  return (
    <button ref={buttonRef} className={styles.toggle} type="button" onClick={onClick}
      title="Bấm để mở trợ lý AI"
      data-chat-trigger data-open={open} data-bounce={bouncing && !open}
      aria-label={open ? "Close heritage AI assistant" : "Open heritage AI assistant"}
      aria-controls={panelId} aria-expanded={open} aria-hidden={open} tabIndex={open ? -1 : 0}>
      <span className={styles.triggerBot}><MilaAvatar /></span>
      <span className={styles.triggerLabel}>Ask AI</span>
      <span className={styles.triggerClose} aria-hidden="true"><CloseOutlined /></span>
      <span className={`${styles.triggerStatus} ${!online ? styles.statusOffline : ""}`}
        role="img" aria-label={online ? "Online" : "Offline"} />
    </button>
  );
}
