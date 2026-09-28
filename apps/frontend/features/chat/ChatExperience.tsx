"use client";
import { theme as antdTheme } from "antd";
import { useCallback, useState } from "react";
import { XProvider } from "@ant-design/x";
import { ChatLanding } from "./components/ChatLanding";
import { ChatView } from "./components/ChatView";
import { CHAT_API_URL, CHAT_SUGGESTIONS } from "./config";
import type { Message, Source } from "./types";
import styles from "./chat.module.css";
import { useHeritageTheme } from "./useHeritageTheme";
import { HelpButton, TopBar } from "./components/TopBar";

const SUGGESTIONS = [
  "Lăng Tự Đức được xây dựng năm nào?",
  "Cao lầu là món gì?",
  "Festival Huế tổ chức mấy năm một lần?",
  "Làng Non Nước nổi tiếng về gì?",
  "Nhã nhạc cung đình Huế có gì đặc biệt?",
];

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
    <XProvider
      theme={{
        algorithm: antdTheme.darkAlgorithm,
        token: {
          colorPrimary: "#FA500F",
          colorBgBase: "#000000",
          colorTextBase: "#ffffff",
          borderRadius: 10,
          fontFamily:
            "Inter, Inter Fallback, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        },
      }}
    >
      <div className={styles.app}>
        <TopBar />
        {!hasMessages ? (
          <ChatLanding
            suggestions={SUGGESTIONS}
            onSend={(t) => send(t)}
            loading={loading}
          />
        ) : (
          <ChatView
            messages={messages}
            input={input}
            loading={loading}
            onInputChange={setInput}
            onSend={() => send()}
          />
        )}

        <HelpButton />
      </div>
    </XProvider>
  );
}
