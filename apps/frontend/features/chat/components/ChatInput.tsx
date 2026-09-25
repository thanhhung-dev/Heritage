"use client";

import { Sender } from "@ant-design/x";
import styles from "../chat.module.css";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  placeholder?: string;
  loading?: boolean;
}

export default function ChatInput({
  value,
  onChange,
  onSubmit,
  placeholder = "Nhắn tin...",
  loading,
}: ChatInputProps) {
  return (
    <Sender
      className={styles.sender}
      value={value}
      onChange={onChange}
      onSubmit={() => {
        if (value.trim()) {
          onSubmit();
        }
      }}
      placeholder={placeholder}
      loading={loading}
    />
  );
}
