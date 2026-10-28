"use client";

import Link from "next/link";
import { PlusOutlined } from "@ant-design/icons";
import type { Conversation } from "../types";
import styles from "@/features/chat/chat.module.css";

interface ConversationSidebarProps {
  authenticated: boolean;
  conversations: Conversation[];
  selectedId: string | null;
  loading: boolean;
  error: string | null;
  hasMore: boolean;
  disabled: boolean;
  onNew: () => void;
  onSelect: (id: string) => void;
  onRetry: () => void;
  onMore: () => void;
}

export function ConversationSidebar({
  authenticated, conversations, selectedId, loading, error, hasMore,
  disabled, onNew, onSelect, onRetry, onMore,
}: ConversationSidebarProps) {
  return (
    <aside className={styles.sidebar} aria-label="Lịch sử trò chuyện">
      <Link href="/" className={styles.sidebarBrand}>HERITAGE</Link>
      <button className={styles.newConversation} type="button" onClick={onNew} disabled={disabled}>
        <PlusOutlined aria-hidden /> Cuộc trò chuyện mới
      </button>
      <h2>Cuộc trò chuyện</h2>
      {!authenticated ? (
        <p className={styles.historyHint}><Link href="/sign-in">Đăng nhập</Link> để xem lịch sử và tiếp tục cuộc trò chuyện của bạn.</p>
      ) : (
        <>
          {error && <div className={styles.historyError} role="alert"><p>{error}</p><button type="button" onClick={onRetry} disabled={loading}>Thử tải lại</button></div>}
          {loading && <p className={styles.historyHint} role="status">Đang tải lịch sử…</p>}
          {!loading && !error && conversations.length === 0 && <p className={styles.historyHint}>Chưa có cuộc trò chuyện nào.</p>}
          <ul className={styles.conversationList}>
            {conversations.map((conversation) => (
              <li key={conversation.id}>
                <button type="button" title={conversation.title} aria-current={selectedId === conversation.id || undefined} onClick={() => onSelect(conversation.id)} disabled={disabled}>
                  {conversation.title}
                </button>
              </li>
            ))}
          </ul>
          {hasMore && <button className={styles.historyMore} type="button" onClick={onMore} disabled={loading}>Tải thêm cuộc trò chuyện</button>}
        </>
      )}
    </aside>
  );
}
