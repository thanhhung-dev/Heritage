"use client";

import type { CSSProperties, HTMLAttributes, Ref } from "react";
import { CloseOutlined } from "@ant-design/icons";
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
  open: boolean;
  online: boolean;
  onClick: () => void;
  buttonRef?: Ref<HTMLButtonElement>;
  dragHandlers?: Pick<HTMLAttributes<HTMLElement>, "onPointerDown" | "onPointerMove" | "onPointerUp"
    | "onPointerCancel" | "onLostPointerCapture" | "onClickCapture" | "onKeyDown">;
  style?: CSSProperties;
  positioned?: boolean;
  dragging?: boolean;
}

export function ChatToggleButton({ panelId, open, online, onClick, buttonRef, dragHandlers, style, positioned, dragging }: ChatToggleButtonProps) {
  return (
    <button ref={buttonRef} className={styles.toggle} type="button" onClick={onClick} {...dragHandlers} style={style}
      data-positioned={positioned} data-dragging={dragging} title="Kéo để di chuyển · Bấm để mở trợ lý AI"
      data-chat-trigger data-open={open} aria-label={open ? "Close heritage AI assistant" : "Open heritage AI assistant"}
      aria-describedby={`${panelId}-drag-help`}
      aria-controls={panelId} aria-expanded={open} aria-hidden={open} tabIndex={open ? -1 : 0}>
      <span className={styles.triggerBot}><MilaAvatar /></span>
      <span className={styles.triggerLabel}>Ask AI</span>
      <span className={styles.triggerClose} aria-hidden="true"><CloseOutlined /></span>
      <span className={`${styles.triggerStatus} ${!online ? styles.statusOffline : ""}`}
        role="img" aria-label={online ? "Online" : "Offline"} />
    </button>
  );
}
