"use client";

import { CloseOutlined, CompressOutlined, ExpandAltOutlined, ReloadOutlined } from "@ant-design/icons";
import { useEffect, useId, useRef, useState, useSyncExternalStore } from "react";
import Aurora from "@/features/chat/components/Aurora";
import { ChatInputBar } from "@/features/chat/components/ChatInputBar";
import { ChatMessageList } from "@/features/chat/components/ChatMessageList";
import { ChatToggleButton } from "@/features/chat/components/ChatToggleButton";
import type { ChatOverlayMessage, ChatOverlayWidgetState } from "@/features/chat/types/chatOverlay";
import styles from "@/features/chat/chat-overlay.module.css";
import { useOverlayDrag } from "@/features/chat/useOverlayDrag";

interface ChatOverlayWidgetProps {
  messages: ChatOverlayMessage[];
  input: string;
  sending: boolean;
  restoring?: boolean;
  disabled?: boolean;
  areaLabel?: string;
  sceneLabel?: string;
  suggestions?: readonly { label: string; value: string }[];
  error: string | null;
  onInputChange: (value: string) => void;
  onSend: (text?: string) => void;
  onNewConversation: () => void;
}

const HERITAGE_LOADING_PALETTES: [string, string, string][] = [
  ["#FA500F", "#FFAD42", "#FA7229"],
  ["#DE4408", "#FF9B2D", "#F0E8DD"],
  ["#C85A17", "#E89B3C", "#FFD28A"],
  ["#FA7229", "#FFB85C", "#F0E8DD"],
];

function buildAmbientClipPath(
  panelWidth: number,
  panelHeight: number,
  box: { x: number; y: number; width: number; height: number },
  radius = 16,
): string {
  const r = Math.min(radius, box.width / 2, box.height / 2);
  const { x, y, width: w, height: h } = box;
  return `path("M 0 0 H ${panelWidth} V ${panelHeight} H 0 Z M ${x + r} ${y} A ${r} ${r} 0 0 0 ${x} ${y + r} V ${y + h - r} A ${r} ${r} 0 0 0 ${x + r} ${y + h} H ${x + w - r} A ${r} ${r} 0 0 0 ${x + w} ${y + h - r} V ${y + r} A ${r} ${r} 0 0 0 ${x + w - r} ${y} Z")`;
}

function subscribeToNetwork(onChange: () => void) {
  window.addEventListener("online", onChange);
  window.addEventListener("offline", onChange);
  return () => {
    window.removeEventListener("online", onChange);
    window.removeEventListener("offline", onChange);
  };
}

export function ChatOverlayWidget(props: ChatOverlayWidgetProps) {
  const panelId = useId();
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLElement>(null);
  const [mode, setMode] = useState<ChatOverlayWidgetState["mode"]>("closed");
  const [justClosed, setJustClosed] = useState(false);
  const isOpen = mode !== "closed";
  const hasConversation = props.messages.some((message) => message.role === "user");
  const showWelcomeGlow = isOpen && !props.sending;
  const showLoadingGlow = isOpen && props.sending;
  const [welcomeGlowMounted, setWelcomeGlowMounted] = useState(false);
  const [loadingGlowMounted, setLoadingGlowMounted] = useState(false);
  const [loadingColors, setLoadingColors] = useState<[string, string, string]>(HERITAGE_LOADING_PALETTES[0]);
  const [ambientClipPath, setAmbientClipPath] = useState<string | undefined>(undefined);
  const panelDrag = useOverlayDrag(panel, { enabled: isOpen, ignoreInteractive: true, layoutKey: mode });
  const online = useSyncExternalStore(subscribeToNetwork, () => navigator.onLine, () => true);

  useEffect(() => {
    const panelEl = panel.current;
    if (!panelEl || !isOpen) return;
    const inputEl = panelEl.querySelector<HTMLElement>("[data-chat-input-row]");
    if (!inputEl) return;

    const updateClip = () => {
      if (panelEl.clientWidth <= 0 || panelEl.clientHeight <= 0) return;
      let x = 0;
      let y = 0;
      let current: HTMLElement | null = inputEl;
      while (current && current !== panelEl) {
        x += current.offsetLeft;
        y += current.offsetTop;
        current = current.offsetParent as HTMLElement | null;
      }
      setAmbientClipPath(
        buildAmbientClipPath(panelEl.clientWidth, panelEl.clientHeight, {
          x,
          y,
          width: inputEl.offsetWidth,
          height: inputEl.offsetHeight,
        }),
      );
    };

    updateClip();
    const observer = new ResizeObserver(updateClip);
    observer.observe(panelEl);
    observer.observe(inputEl);
    if (inputEl.parentElement) observer.observe(inputEl.parentElement);
    return () => observer.disconnect();
  }, [isOpen, mode, props.messages.length, props.restoring, props.error]);

  useEffect(() => {
    if (!isOpen) { setWelcomeGlowMounted(false); return; }
    if (showWelcomeGlow) { setWelcomeGlowMounted(true); return; }
    const timer = window.setTimeout(() => setWelcomeGlowMounted(false), 350);
    return () => window.clearTimeout(timer);
  }, [isOpen, showWelcomeGlow]);

  useEffect(() => {
    if (!isOpen) { setLoadingGlowMounted(false); return; }
    if (showLoadingGlow) {
      const palette =
        HERITAGE_LOADING_PALETTES[Math.floor(Math.random() * HERITAGE_LOADING_PALETTES.length)];
      setLoadingColors(palette);
      setLoadingGlowMounted(true);
      return;
    }
    // Keep the canvas alive until the 450ms reply outro has finished.
    const timer = window.setTimeout(() => setLoadingGlowMounted(false), 450);
    return () => window.clearTimeout(timer);
  }, [isOpen, showLoadingGlow]);

  useEffect(() => {
    if (!panel.current) return;
    panel.current.inert = !isOpen;
    if (isOpen) panel.current.querySelector("textarea")?.focus();
  }, [isOpen]);
  const close = () => {
    setJustClosed(true);
    setMode("closed");
    requestAnimationFrame(() => trigger.current?.focus());
  };
  const open = () => {
    setJustClosed(false);
    setMode("open");
  };

  return (
    <div className={styles.dock} data-chat-overlay onPointerDown={(event) => event.stopPropagation()}
      onWheel={(event) => event.stopPropagation()} onKeyDown={(event) => {
        event.stopPropagation();
        if (event.key === "Escape" && mode !== "closed") { event.preventDefault(); close(); }
      }}>
      <span id={`${panelId}-drag-help`} className={styles.dragHint}>
        Kéo thanh tiêu đề để di chuyển cửa sổ chat. Dùng phím mũi tên khi được chọn; giữ Shift để di chuyển nhanh hơn.
      </span>
      <ChatToggleButton panelId={panelId} open={isOpen} bouncing={justClosed} online={online} buttonRef={trigger}
        onClick={() => isOpen ? close() : open()} />
        <section ref={panel} id={panelId} data-chat-panel data-open={isOpen}
          data-chat-phase={props.sending ? "thinking" : hasConversation ? "conversation" : "welcome"}
          style={panelDrag.style} data-positioned={Boolean(panelDrag.position)} data-dragging={panelDrag.dragging}
          className={`${styles.panel} ${mode === "expanded" ? styles.panelExpanded : ""}`}
          role="dialog" aria-modal={false} aria-hidden={!isOpen}
          aria-label={["Heritage AI assistant", props.areaLabel, props.sceneLabel].filter(Boolean).join(" · ")}>
          <div
            className={styles.ambient}
            aria-hidden="true"
            style={ambientClipPath ? { clipPath: ambientClipPath, WebkitClipPath: ambientClipPath } : undefined}
          >
            <div className={`${styles.ambientMotion} ${styles.ambientBottom}`}
              data-aurora-edge="bottom" data-active={showWelcomeGlow}>
              {isOpen && welcomeGlowMounted && (
                <Aurora colorStops={["#FA500F", "#FFAD42", "#FA7229"]}
                  amplitude={1.45} blend={.42} height={.22} scale={2.2} glow={.52} layers={2}
                  direction="bottom" speed={1.2} opacity={.58} dpr={1.5}
                  mouseInteraction={false} />
              )}
            </div>
            <div className={`${styles.ambientMotion} ${styles.ambientTop}`}
              data-aurora-edge="top" data-active={showLoadingGlow}>
              {isOpen && loadingGlowMounted && (
                <Aurora colorStops={loadingColors} className={styles.ambientColors}
                  amplitude={1.4} blend={.42} height={.22} scale={2.2} glow={.52} layers={2}
                  speed={1.1} opacity={.58} dpr={1.5} mouseInteraction={false} intro={false} />
              )}
            </div>
          </div>
          <header className={styles.header} {...panelDrag.handlers} data-chat-drag-handle tabIndex={isOpen ? 0 : -1}
            role="group" aria-label="Di chuyển cửa sổ chat" aria-describedby={`${panelId}-drag-help`}
            title="Kéo để di chuyển cửa sổ chat">
            <div className={styles.headerActions}>
              <button type="button" onClick={props.onNewConversation} aria-label="Start a new conversation" title="New conversation">
                <ReloadOutlined />
              </button>
              <button type="button" aria-label={mode === "expanded" ? "Restore chat size" : "Expand chat"}
                aria-pressed={mode === "expanded"} onClick={() => setMode(mode === "expanded" ? "open" : "expanded")}>
                {mode === "expanded" ? <CompressOutlined /> : <ExpandAltOutlined />}
              </button>
              <button type="button" onClick={close} aria-label="Close assistant"><CloseOutlined /></button>
            </div>
          </header>
          <ChatMessageList messages={props.messages} sending={props.sending} onSend={props.onSend}
            hideWelcome={hasConversation || props.input.trim().length > 0} />
          {props.restoring && <p className={styles.restoreStatus} role="status">Đang khôi phục hội thoại…</p>}
          {props.error && <p className={styles.error} role="alert">{props.error}</p>}
          <ChatInputBar value={props.input} sending={props.sending} disabled={props.restoring || props.disabled}
            contextLabel={props.sceneLabel}
            suggestions={props.suggestions}
            showSuggestions={(props.suggestions !== undefined || props.messages.length <= 1) && !props.restoring && !props.disabled}
            onChange={props.onInputChange} onSend={props.onSend} />
        </section>
    </div>
  );
}
