"use client";

import { useCallback, useState } from "react";
import { XProvider } from "@ant-design/x";
import { theme as antdTheme } from "antd";
import { TopBar, HelpButton } from "@/components/TopBar";
import { Landing } from "@/components/Landing";
import { ChatView } from "@/components/ChatView";
import type { Message, Source } from "@/types/chat";

const SUGGESTIONS = [
  "Lăng Tự Đức được xây dựng năm nào?",
  "Cao lầu là món gì?",
  "Festival Huế tổ chức mấy năm một lần?",
  "Làng Non Nước nổi tiếng về gì?",
  "Nhã nhạc cung đình Huế có gì đặc biệt?",
];

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const hasMessages = messages.length > 0;

  const send = useCallback(
    async (text?: string) => {
      const userMsg = text ?? input;
      if (!userMsg.trim() || loading) return;

      const newUserMsg: Message = {
        id: Date.now().toString(),
        role: "user",
        content: userMsg,
      };
      setMessages((m) => [...m, newUserMsg]);
      setInput("");
      setLoading(true);

      try {
        const res = await fetch(`${API_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: userMsg, use_rag: true }),
        });
        const data = await res.json();
        console.log("API Response:" , data);
        console.log("API Response:", data.answer);
        console.log("API Response:", data.sources);
        const botMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: data.answer,
          sources: data.sources as Source[],
          correctedFrom: data.corrected_from,
          correctedTo: data.corrected_to,
        };
        setMessages((m) => [...m, botMsg]);
      } catch {
        setMessages((m) => [
          ...m,
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
    [input, loading]
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
      <div className="app">
        <TopBar />

        {!hasMessages ? (
          <Landing
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
