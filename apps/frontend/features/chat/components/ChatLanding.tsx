"use client";

import ChatInput from "./ChatInput";
import { SuggestionList } from "./SuggestionList";
import { HeritageLogo } from "@/components/Logo/HeritageLogo";
import styles from "@/features/chat/chat.module.css";

interface LandingProps {
  input: string;
  onInputChange: (value: string) => void;
  onSend: (text: string) => void;
  suggestions: string[];
  loading?: boolean;
}

export function ChatLanding({ input, onInputChange, onSend, suggestions, loading }: LandingProps) {
  return (
    <div className={styles.landing}>
      <div className={styles.landingWelcome}>
        <HeritageLogo size={64} />
        <h1 className={styles.landingGreeting} data-hidden={input.trim().length > 0}
          aria-hidden={input.trim().length > 0}>
          Bạn muốn khám phá di sản nào?
        </h1>
      </div>

      <div className={styles.landingInput}>
        <ChatInput
          value={input}
          onChange={onInputChange}
          onSubmit={() => {
            if (input.trim()) {
              onSend(input);
            }
          }}
          placeholder="Hỏi về di sản Đà Nẵng – Huế…"
          loading={loading}
        />
      </div>

      <SuggestionList suggestions={suggestions} onSelect={onSend} />
    </div>
  );
}
