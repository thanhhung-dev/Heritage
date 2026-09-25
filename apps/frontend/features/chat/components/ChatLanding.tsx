"use client";

import { useState } from "react";
import { Welcome } from "@ant-design/x";
import ChatInput from "./ChatInput";
import { SuggestionList } from "./SuggestionList";
import { HeritageLogo } from "@/components/Logo/HeritageLogo";
import styles from "../chat.module.css";

interface LandingProps {
  onSend: (text: string) => void;
  suggestions: string[];
  loading?: boolean;
}

export function ChatLanding({ onSend, suggestions, loading }: LandingProps) {
  const [input, setInput] = useState("");

  return (
    <div className={styles.landing}>
      <Welcome
        variant="borderless"
        icon={<HeritageLogo size={64} />}
      />

      <div className={styles.landingInput}>
        <ChatInput
          value={input}
          onChange={setInput}
          onSubmit={() => {
            if (input.trim()) {
              onSend(input);
              setInput("");
            }
          }}
          placeholder="Hỏi về di sản Đà Nẵng - Huế…"
          loading={loading}
        />
      </div>

      <SuggestionList suggestions={suggestions} onSelect={onSend} />
    </div>
  );
}
