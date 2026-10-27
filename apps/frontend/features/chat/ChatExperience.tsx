"use client";
import { Alert, Drawer, Spin } from "antd";
import { useState, useSyncExternalStore } from "react";
import { XProvider } from "@ant-design/x";
import { ChatLanding } from "./components/ChatLanding";
import { ChatView } from "./components/ChatView";
import { CHAT_SUGGESTIONS } from "./config";
import styles from "@/features/chat/chat.module.css";
import { useHeritageTheme } from "./useHeritageTheme";
import { HelpButton, TopBar } from "./components/TopBar";
import { ConversationSidebar } from "./components/ConversationSidebar";
import { useChatConversations } from "./useChatConversations";
import { AUTH_CHANGE_EVENT, getAccessToken } from "@/lib/auth";

function subscribeToSession(onChange: () => void) {
  window.addEventListener(AUTH_CHANGE_EVENT, onChange);
  window.addEventListener("storage", onChange);
  return () => {
    window.removeEventListener(AUTH_CHANGE_EVENT, onChange);
    window.removeEventListener("storage", onChange);
  };
}

const serverSession = () => null;

export function ChatExperience() {
  const token = useSyncExternalStore(subscribeToSession, getAccessToken, serverSession);
  // Remount on session changes so another account never sees the previous account's state.
  return <ChatSession key={token ?? "guest"} accessToken={token} />;
}

function ChatSession({ accessToken }: { accessToken: string | null }) {
  const chat = useChatConversations(accessToken);
  const theme = useHeritageTheme();
  const [historyOpen, setHistoryOpen] = useState(false);
  const sidebar = (
    <ConversationSidebar
      authenticated={Boolean(accessToken)}
      conversations={chat.conversations}
      selectedId={chat.conversationId}
      loading={chat.historyLoading}
      error={chat.historyError}
      hasMore={chat.hasMore}
      disabled={chat.sending || chat.reading}
      onNew={() => { chat.newConversation(); setHistoryOpen(false); }}
      onSelect={(id) => { void chat.selectConversation(id); setHistoryOpen(false); }}
      onRetry={() => void chat.refreshHistory()}
      onMore={() => void chat.refreshHistory(true)}
    />
  );
  return (
    <XProvider theme={theme}>
      <div className={styles.app}>
        <div className={styles.desktopHistory}>{sidebar}</div>
        <div className={styles.workspace} data-error={Boolean(chat.error) || undefined}>
          <TopBar authenticated={Boolean(accessToken)} onHistory={() => setHistoryOpen(true)} />
          {chat.error && <Alert className={styles.chatError} type="error" showIcon message={chat.error} role="alert" />}
          {chat.reading ? (
            <div className={styles.historySpinner} role="status"><Spin /><span>Đang tải cuộc trò chuyện…</span></div>
          ) : chat.messages.length === 0 ? (
            <ChatLanding
              suggestions={[...CHAT_SUGGESTIONS]}
              input={chat.input}
              onInputChange={chat.setInput}
              onSend={(text) => void chat.send(text)}
              loading={chat.sending}
            />
          ) : (
            <ChatView
              messages={chat.messages}
              input={chat.input}
              loading={chat.sending}
              onInputChange={chat.setInput}
              onSend={(text) => void chat.send(text)}
            />
          )}
        </div>
        <Drawer title="Lịch sử trò chuyện" placement="left" open={historyOpen} onClose={() => setHistoryOpen(false)} width={290} styles={{ body: { padding: 0 } }}>
          {sidebar}
        </Drawer>
        <HelpButton />
      </div>
    </XProvider>
  );
}
