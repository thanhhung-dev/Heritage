"use client";

import { useEffect, useRef } from "react";
import { Bubble, Sources } from "@ant-design/x";
import type { BubbleListProps } from "@ant-design/x";
import type { Message, Source } from "@/types/chat";
import ChatInput from "./ChatInput";
import { ChatActions } from "./ChatActions";
import { HeritageLogo } from "./Logo/HeritageLogo";
import { HeritageLogoMini } from "./Logo/HeritageLogoMinimal";

interface ChatViewProps {
  messages: Message[];
  input: string;
  loading: boolean;
  onInputChange: (value: string) => void;
  onSend: (text?: string) => void;
}

function SourceFooter({ sources }: { sources: Source[] }) {
  return (
    <Sources
      title="Nguồn"
      items={sources.map((s, i) => ({
        key: i,
        title: s.doc || "Nguồn",
        description: s.heading,
        url: s.url,
      }))}
    />
  );
}

export function ChatView({
  messages,
  input,
  loading,
  onInputChange,
  onSend,
}: ChatViewProps) {
  const listRef = useRef<React.ComponentRef<typeof Bubble.List>>(null);

  useEffect(() => {
    const box = listRef.current?.scrollBoxNativeElement;
    if (box) {
      box.scrollTo({ top: box.scrollHeight, behavior: "smooth" });
    }
  }, [messages, loading]);

  const items: BubbleListProps["items"] = [
    ...messages.map((msg) => ({
      key: msg.id,
      role: msg.role === "user" ? "user" : "ai",
      content: msg.content,
      footer:
        msg.role === "assistant" ? (
          <div className="assistant-footer">
            <ChatActions content={msg.content} />
            {msg.sources && msg.sources.length > 0 && (
              <SourceFooter sources={msg.sources} />
            )}
          </div>
        ) : undefined,
    })),
    ...(loading
      ? [
          {
            key: "typing",
            role: "ai",
            avatar: null,
            content: (
              <div className="thinking-spin">
                <div className="thinking-spin-ring">
                  <div className="thingking-logo">
                    <HeritageLogoMini size={28}/>
                  </div>
                </div>
                <span className="thinking-spin-text">Đang suy nghĩ…</span>
              </div>
            ),
          },
        ]
      : []),
  ];

  return (
    <>
      <Bubble.List
        ref={listRef}
        className="chat-messages"
        autoScroll={false}
        styles={{ scroll: { height: "100%" } }}
        items={items}
        role={{
          user: {
            placement: "end",
            variant: "filled",
            shape: "corner",
          },
          ai: {
            placement: "start",
            variant: "borderless",
            avatar: <HeritageLogoMini size={28} />,
          },
        }}
      />

      <div className="input-area">
        <div className="input-area-inner">
          <ChatInput
            value={input}
            onChange={onInputChange}
            onSubmit={() => onSend()}
            placeholder="Hỏi thêm…"
            loading={loading}
          />
          <div className="input-area-disclaimer">
            HeritageGraph có thể mắc lỗi. Kiểm tra thông tin. · 100% local
          </div>
        </div>
      </div>
    </>
  );
}
