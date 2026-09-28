"use client";

import { useCallback, useState } from "react";
import { XProvider } from "@ant-design/x";
import { ChatLanding } from "./components/ChatLanding";
import { ChatView } from "./components/ChatView";
import { CHAT_API_URL, CHAT_SUGGESTIONS } from "./config";
import type { Message, Source } from "./types";
import styles from "./chat.module.css";
import { useHeritageTheme } from "./useHeritageTheme";

export function ChatExperience() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const theme = useHeritageTheme();

  const hasMessages = messages.length > 0;

  const send = useCallback(
    async (text?: string) => {
      const userMessage = text ?? input;
      if (!userMessage.trim() || loading) return;

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: Date.now().toString(),
          role: "user",
          content: userMessage,
        },
      ]);
      setInput("");
      setLoading(true);

      try {
        const response = await fetch(`${CHAT_API_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: userMessage, use_rag: true }),
        });
        if (!response.ok) throw new Error("Chat request failed");

        const data = await response.json();

        setMessages((currentMessages) => [
          ...currentMessages,
          {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            content: data.answer,
            sources: data.sources as Source[],
            correctedFrom: data.corrected_from,
            correctedTo: data.corrected_to,
          },
        ]);
      } catch {
        setMessages((currentMessages) => [
          ...currentMessages,
          {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            content: "Đã xảy ra lỗi khi kết nối tới máy chủ.",
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [input, loading],
  );

  return (
    <XProvider theme={theme}>
      <section className={styles.experience} aria-label="Trợ lý di sản">
        {hasMessages ? (
          <ChatView
            messages={messages}
            input={input}
            loading={loading}
            onInputChange={setInput}
            onSend={() => send()}
          />
        ) : (
          <ChatLanding
            suggestions={[...CHAT_SUGGESTIONS]}
            onSend={(message) => send(message)}
            loading={loading}
          />
        )}

      </section>
    </XProvider>
  );
}
