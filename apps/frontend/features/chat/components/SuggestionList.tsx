"use client";

import { Prompts } from "@ant-design/x";
import type { PromptsProps } from "@ant-design/x";
import styles from "../chat.module.css";

interface SuggestionListProps {
  suggestions: string[];
  onSelect: (text: string) => void;
  compact?: boolean;
}

export function SuggestionList({ suggestions, onSelect, compact = false }: SuggestionListProps) {
  const items: PromptsProps["items"] = suggestions.map((text) => ({
    key: text,
    label: text,
  }));

  return (
    <Prompts
      className={`${styles.suggestionList} ${compact ? styles.compactSuggestionList : ""}`}
      title="Câu hỏi gợi ý"
      wrap
      items={items}
      onItemClick={({ data }) => {
        if (typeof data.label === "string") {
          onSelect(data.label);
        }
      }}
    />
  );
}
