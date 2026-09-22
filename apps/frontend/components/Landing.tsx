"use client";

import { useState } from "react";
import { Welcome } from "@ant-design/x";
import ChatInput from "./ChatInput";
import { SuggestionList } from "./Suggestion";
import { HeritageLogo } from "./Logo/HeritageLogo";

interface LandingProps {
  onSend: (text: string) => void;
  suggestions: string[];
  loading?: boolean;
}

export function Landing({ onSend, suggestions, loading }: LandingProps) {
  const [input, setInput] = useState("");

  return (
    <div className="landing">
      <Welcome
        variant="borderless"
        icon={<HeritageLogo size={64} />}
      />

      <div className="landing-input">
        <ChatInput
          value={input}
          onChange={setInput}
          onSubmit={() => {
            if (input.trim()) {
              onSend(input);
              setInput("");
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