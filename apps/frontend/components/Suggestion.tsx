"use client";

import { Prompts } from "@ant-design/x";
import type { PromptsProps } from "@ant-design/x";

interface SuggestionListProps {
  suggestions: string[];
  onSelect: (text: string) => void;
}

export function SuggestionList({ suggestions, onSelect }: SuggestionListProps) {
  const items: PromptsProps["items"] = suggestions.map((text) => ({
    key: text,
    label: text,
  }));

  return (
    <Prompts
      className="suggestion-list"
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