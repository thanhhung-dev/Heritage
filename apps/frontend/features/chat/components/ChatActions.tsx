"use client";

import { useEffect, useRef, useState } from "react";
import {
  CheckOutlined, CopyOutlined, DislikeFilled, DislikeOutlined,
  DownloadOutlined, LikeFilled, LikeOutlined, MoreOutlined,
} from "@ant-design/icons";
import styles from "@/features/chat/components/ChatActions.module.css";

interface ChatActionsProps {
  content: string;
}

type Reaction = "like" | "dislike" | null;

export function ChatActions({ content }: ChatActionsProps) {
  const [copied, setCopied] = useState(false);
  const [copying, setCopying] = useState(false);
  const [error, setError] = useState("");
  const [reaction, setReaction] = useState<Reaction>(null);
  const menu = useRef<HTMLDetailsElement>(null);

  useEffect(() => {
    if (!copied) return;
    const timer = window.setTimeout(() => setCopied(false), 3000);
    return () => window.clearTimeout(timer);
  }, [copied]);

  async function copy() {
    setCopying(true);
    setError("");
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
    } catch {
      setError("Không thể sao chép. Vui lòng thử lại.");
    } finally {
      setCopying(false);
    }
  }

  return (
    <div className={styles.root}>
      <div className={styles.actions} role="group" aria-label="Thao tác với câu trả lời">
        <button type="button" className={styles.button} disabled={copying || copied}
          aria-label={copied ? "Đã sao chép" : "Sao chép câu trả lời"}
          title={copied ? "Đã sao chép" : "Sao chép"} data-active={copied}
          onClick={() => void copy()}>
          {copied ? <CheckOutlined /> : <CopyOutlined />}
        </button>
        <button type="button" className={styles.button} aria-label="Câu trả lời hữu ích"
          title="Hữu ích" aria-pressed={reaction === "like"}
          onClick={() => setReaction(reaction === "like" ? null : "like")}>
          {reaction === "like" ? <LikeFilled /> : <LikeOutlined />}
        </button>
        <button type="button" className={styles.button} aria-label="Câu trả lời chưa hữu ích"
          title="Chưa hữu ích" aria-pressed={reaction === "dislike"}
          onClick={() => setReaction(reaction === "dislike" ? null : "dislike")}>
          {reaction === "dislike" ? <DislikeFilled /> : <DislikeOutlined />}
        </button>
        <details ref={menu} className={styles.more} onKeyDown={(event) => {
          if (event.key === "Escape" && menu.current) {
            menu.current.open = false;
            menu.current.querySelector("summary")?.focus();
          }
        }}>
          <summary className={styles.button} aria-label="Thao tác khác" title="Thao tác khác">
            <MoreOutlined />
          </summary>
          <div className={styles.popup}>
            <a className={styles.download} download="heritage-answer.md"
              href={`data:text/markdown;charset=utf-8,${encodeURIComponent(content)}`}
              onClick={() => { if (menu.current) menu.current.open = false; }}>
              <DownloadOutlined aria-hidden="true" /> Xuất Markdown
            </a>
          </div>
        </details>
      </div>
      <span className={styles.status} role="status">{copied ? "Đã sao chép câu trả lời" : ""}</span>
      {error && <span className={styles.error} role="alert">{error}</span>}
    </div>
  );
}
