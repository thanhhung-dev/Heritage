'use client';

import React, { useState, useRef, useEffect, KeyboardEvent } from 'react';
import styles from '@/features/gemini-preview/components/GeminiChatClone.module.css';

interface ChatMessage {
  id: string;
  role: 'user' | 'model';
  text: string;
}

const SUGGESTED_PROMPTS = [
  'Giúp tôi đưa ra quyết định',
  'Giúp tôi phân tích một khái niệm mới',
  'Giúp tôi viết nội dung',
];

function GeminiSparkleIcon({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <path
        d="M14 2C14.6 8.2 19.8 13.4 26 14C19.8 14.6 14.6 19.8 14 26C13.4 19.8 8.2 14.6 2 14C8.2 13.4 13.4 8.2 14 2Z"
        fill="url(#gemini-sparkle-grad)"
      />
      <defs>
        <linearGradient id="gemini-sparkle-grad" x1="2" y1="2" x2="26" y2="26" gradientUnits="userSpaceOnUse">
          <stop stopColor="#4285F4" />
          <stop offset="0.5" stopColor="#9B72CB" />
          <stop offset="1" stopColor="#D96570" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export default function GeminiChatClone() {
  const [animKey, setAnimKey] = useState(0);
  const [startMode, setStartMode] = useState<'cold' | 'warm'>('cold');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (typeof window !== 'undefined' && 'CSS' in window && 'registerProperty' in window.CSS) {
      try {
        window.CSS.registerProperty({
          name: '--mask-angle',
          syntax: '<angle>',
          inherits: false,
          initialValue: '180deg',
        });
      } catch {
        // Already registered
      }
    }
  }, []);

  const handleSend = (textToSend?: string) => {
    const trimmed = (textToSend ?? input).trim();
    if (!trimmed) return;

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: trimmed,
    };
    const modelMsg: ChatMessage = {
      id: `m-${Date.now() + 1}`,
      role: 'model',
      text: `Mình đã nhận yêu cầu: "${trimmed}". Đây là bản xem trước giao diện Gemini in Chrome Side Panel (1:1 clone).`,
    };

    setMessages((prev) => [...prev, userMsg, modelMsg]);
    setInput('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleReplay = (mode: 'cold' | 'warm' = startMode) => {
    setStartMode(mode);
    setMessages([]);
    setInput('');
    setAnimKey((k) => k + 1);
  };

  return (
    <div className={styles.stage}>
      <div className={styles.stageControls}>
        <button type="button" className={styles.replayBtn} onClick={() => handleReplay('cold')}>
          ↻ Cold Start (Quét ánh sáng 1.5s)
        </button>
        <button type="button" className={styles.replayBtn} onClick={() => handleReplay('warm')}>
          ⚡ Warm Start (Chớp sáng 0.67s)
        </button>
      </div>

      <main key={animKey} className={styles.sidePanel} aria-label="Gemini trong Chrome">
        {/* Luminous Gradient Aura (1:1 keyframes & rings) */}
        <div
          className={`${styles.luminousGradientContainer} ${
            messages.length > 0
              ? styles.gradientHidden
              : startMode === 'cold'
                ? styles.coldStart
                : styles.warmStart
          }`}
          aria-hidden="true"
        >
          <div className={styles.energyWrapper}>
            <div className={`${styles.energyRing} ${styles.outerRing}`} />
            <div className={`${styles.energyRing} ${styles.innerRing}`} />
          </div>
        </div>

        {/* Topbar */}
        <header className={styles.topbarContainer}>
          <div className={styles.conversationTitle}>
            {messages.length > 0 ? messages[0].text : ''}
          </div>

          <div className={styles.actionsContainer}>
            <button type="button" className={styles.profileButton} title="Tài khoản được quản lý">
              <span className={styles.enterpriseChip} aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 7V3H2v18h20V7H12zM6 19H4v-2h2v2zm0-4H4v-2h2v2zm0-4H4V9h2v2zm0-4H4V5h2v2zm4 12H8v-2h2v2zm0-4H8v-2h2v2zm0-4H8V9h2v2zm0-4H8V5h2v2zm10 12h-8v-2h2v-2h-2v-2h2v-2h-2V9h8v10zm-2-8h-2v2h2v-2zm0 4h-2v2h2v-2z" />
                </svg>
              </span>
              <span className={styles.enterpriseLabel}>Được quản lý</span>
              <span className={styles.avatarCircle}>D</span>
            </button>

            <button type="button" className={styles.iconBtn} aria-label="Tùy chọn khác" title="Tùy chọn khác">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <circle cx="12" cy="5" r="2" />
                <circle cx="12" cy="12" r="2" />
                <circle cx="12" cy="19" r="2" />
              </svg>
            </button>

            <button type="button" className={styles.iconBtn} aria-label="Ghim bảng điều khiển" title="Ghim bảng điều khiển">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <rect x="3" y="4" width="18" height="16" rx="2" />
                <line x1="15" y1="4" x2="15" y2="20" />
              </svg>
            </button>

            <button
              type="button"
              className={styles.iconBtn}
              aria-label="Đóng Gemini trong Chrome"
              title="Đóng Gemini trong Chrome"
              onClick={() => handleReplay()}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="6" y1="6" x2="18" y2="18" />
                <line x1="18" y1="6" x2="6" y2="18" />
              </svg>
            </button>
          </div>
        </header>

        {/* Main Content */}
        <section className={styles.mainContent}>
          {messages.length === 0 ? (
            <div className={styles.zeroState}>
              <div className={styles.sparkleLogo}>
                <GeminiSparkleIcon size={36} />
              </div>
              <h1 className={styles.greetingsContainer}>Dương ơi, đến lượt bạn rồi!</h1>
              <div className={styles.promptContainer}>
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className={styles.promptButton}
                    onClick={() => handleSend(prompt)}
                  >
                    <span>{prompt}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className={styles.messagesList}>
              {messages.map((msg) =>
                msg.role === 'user' ? (
                  <div key={msg.id} className={styles.userBubble}>
                    {msg.text}
                  </div>
                ) : (
                  <div key={msg.id} className={styles.modelRow}>
                    <div style={{ flexShrink: 0, marginTop: 2 }}>
                      <GeminiSparkleIcon size={20} />
                    </div>
                    <div className={styles.modelText}>{msg.text}</div>
                  </div>
                )
              )}
            </div>
          )}
        </section>

        {/* Bottom Input Area */}
        <div className={styles.inputAreaWrapper}>
          <div className={styles.inputCard}>
            <textarea
              ref={textareaRef}
              className={styles.textarea}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Trò chuyện với Gemini"
              aria-label="Trò chuyện với Gemini"
            />
            <div className={styles.inputFooter}>
              <div className={styles.inputLeftActions}>
                <button
                  type="button"
                  className={styles.attachBtn}
                  aria-label="Thêm tệp đính kèm"
                  title="Thêm tệp đính kèm (Add any files)"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="12" y1="5" x2="12" y2="19" />
                    <line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                </button>
              </div>

              <div className={styles.inputRightActions}>
                <button type="button" className={styles.modelPill} title="Chọn mô hình">
                  <span>Hydrogen</span>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>

                {input.trim() ? (
                  <button
                    type="button"
                    className={styles.sendBtn}
                    aria-label="Gửi"
                    onClick={() => handleSend()}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
                    </svg>
                  </button>
                ) : (
                  <button type="button" className={styles.micBtn} aria-label="Sử dụng micrô" title="Sử dụng micrô">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <rect x="9" y="2" width="6" height="11" rx="3" />
                      <path d="M5 10a7 7 0 0 0 14 0" />
                      <line x1="12" y1="17" x2="12" y2="21" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
