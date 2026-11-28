"use client";

import { DownOutlined, LoadingOutlined } from "@ant-design/icons";
import styles from "@/features/chat/components/ChatProcessing.module.css";

interface ChatProcessingProps {
  question: string;
}

export function ChatProcessing({ question }: ChatProcessingProps) {
  return (
    <details className={styles.root}>
      <summary className={styles.trigger}>
        <DownOutlined className={styles.chevron} aria-hidden="true" />
        <span className={styles.label} role="status">Đang xử lý câu hỏi</span>
      </summary>
      <div className={styles.panel}>
        <span className={styles.caption}>Câu hỏi</span>
        <p className={styles.question}>{question || "Đang gửi yêu cầu…"}</p>
        <p className={styles.hint}>Đang chờ phản hồi từ trợ lý.</p>
      </div>
    </details>
  );
}
