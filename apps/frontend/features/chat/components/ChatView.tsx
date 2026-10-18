"use client";

import { useEffect, useRef } from "react";
import { Bubble, Sources } from "@ant-design/x";
import type { BubbleListProps } from "@ant-design/x";
import type { Message, Source } from "@/features/chat/types";
import ChatInput from "./ChatInput";
import { ChatActions } from "./ChatActions";
import { HeritageLogoMini } from "@/components/Logo/HeritageLogoMinimal";
import styles from "../chat.module.css";

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
          <div className={styles.assistantFooter}>
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
              <div className={styles.thinking}>
                <div className={styles.thinkingRing}>
                  <div className={styles.thinkingLogo}>
                    <HeritageLogoMini size={28} />
                  </div>
                </div>
                <span className={styles.thinkingText}>Đang suy nghĩ…</span>
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
        className={styles.messages}
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

      <div className={styles.inputArea}>
        <div className={styles.inputAreaInner}>
          <ChatInput
            value={input}
            onChange={onInputChange}
            onSubmit={() => onSend()}
            placeholder="Hỏi thêm…"
            loading={loading}
          />
          <div className={styles.disclaimer}>
            HeritageGraph có thể mắc lỗi. Kiểm tra thông tin. · 100% local
          </div>
        </div>
      </div>
    </>
  );
}
