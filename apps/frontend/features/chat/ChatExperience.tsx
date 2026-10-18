"use client";

import { useCallback, useState } from "react";
import { XProvider } from "@ant-design/x";
import { apiClient } from "@/config/api";
import type { components } from "@/types/api.generated";
import { ChatLanding } from "./components/ChatLanding";
import { ChatView } from "./components/ChatView";
import { CHAT_SUGGESTIONS } from "./config";
import type { Message, Source } from "./types";
import styles from "./chat.module.css";
import { useHeritageTheme } from "./useHeritageTheme";

type ChatRequest = components["schemas"]["ChatRequest"];
type ChatResponse = components["schemas"]["ChatResponse"];

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
        const request: ChatRequest = { message: userMessage, use_rag: true };
        const data = await apiClient<ChatResponse>("/api/chat", {
          method: "POST",
          body: JSON.stringify(request),
        });

        setMessages((currentMessages) => [
          ...currentMessages,
          {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            content: data.answer,
            sources: (data.sources ?? []).map(
              ({ text, doc, url, heading, chunk_id }): Source => ({
                text: text ?? undefined,
                doc: doc ?? undefined,
                url: url ?? undefined,
                heading: heading ?? undefined,
                chunk_id: chunk_id ?? undefined,
              }),
            ),
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
