"use client";
import { theme as antdTheme } from "antd";
import { useEffect, useState } from "react";
import { XProvider } from "@ant-design/x";
import { ChatLanding } from "./components/ChatLanding";
import { ChatView } from "./components/ChatView";
import { CHAT_SUGGESTIONS } from "./config";
import type { Message } from "./types";
import styles from "@/features/chat/chat.module.css";
import { useHeritageTheme } from "./useHeritageTheme";
import { HelpButton, TopBar } from "./components/TopBar";
import { AUTH_CHANGE_EVENT } from "@/lib/auth";
import { getConversationAccountId, useConversationSession } from "@/hooks/useConversationSession";

const SUGGESTIONS = [...CHAT_SUGGESTIONS];

function initialStandaloneMessages(): Message[] { return []; }

export function ChatExperience() {
  const [account, setAccount] = useState(getConversationAccountId);
  useEffect(() => {
    const update = () => setAccount(getConversationAccountId());
    window.addEventListener(AUTH_CHANGE_EVENT, update);
    return () => window.removeEventListener(AUTH_CHANGE_EVENT, update);
  }, []);
  return <AccountChatExperience key={account ?? "guest"} />;
}

function AccountChatExperience() {
  const chat = useConversationSession({ scope: "standalone", initialMessages: initialStandaloneMessages });
  const { messages, input, sending: loading, setInput, send } = chat;
  const theme = useHeritageTheme();
  const hasMessages = messages.length > 0;

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
      <div
        className={styles.app}
        data-chat-phase={loading ? "thinking" : hasMessages ? "conversation" : "welcome"}
      >
        <div className={styles.atmosphere} aria-hidden="true" />
        <TopBar />
        {!hasMessages ? (
          <ChatLanding
            input={input}
            onInputChange={setInput}
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

        {chat.error && <p className={styles.requestError} role="alert">{chat.error}</p>}
        <HelpButton />
      </div>
    </XProvider>
  );
}
