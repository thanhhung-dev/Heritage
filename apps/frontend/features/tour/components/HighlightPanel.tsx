"use client";

import { useEffect, useRef } from "react";
import type { HeritageInteractiveHighlight } from "@/types/heritage";
import styles from "../styles.module.css";

export default function HighlightPanel({ highlight, onClose }: {
  highlight: HeritageInteractiveHighlight | null;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const highlightId = highlight?.id;
  useEffect(() => {
    if (highlightId === undefined) return;
    const active = document.activeElement;
    if (active instanceof HTMLElement && active !== closeRef.current) returnFocus.current = active;
    closeRef.current?.focus();
  }, [highlightId]);
  const close = () => {
    const trigger = returnFocus.current;
    onClose();
    // Đợi popup đóng để panel điểm tương tác trên màn hình thấp hiện lại.
    requestAnimationFrame(() => trigger?.focus());
  };
  if (!highlight) return null;
  const mediaUrl = highlight.media_url && /^(https?:\/\/|\/(?!\/))/i.test(highlight.media_url) ? highlight.media_url : null;
  return (
    <aside id="hotspot-popup" className={styles.hotspotPopup} aria-labelledby="hotspot-popup-title" aria-describedby="hotspot-popup-text"
      onKeyDown={(event) => { if (event.key === "Escape") { event.stopPropagation(); close(); } }}>
      <button ref={closeRef} className={styles.hotspotPopupClose} type="button" aria-label="Close highlight" onClick={close}>&times;</button>
      <h2 id="hotspot-popup-title">{highlight.popup_title ?? "Highlight"}</h2>
      <p id="hotspot-popup-text">{highlight.popup_text}</p>
      {/* Schema hiện chỉ có media_url, chưa có MIME/type: không đoán ảnh/video từ đuôi URL. */}
      {mediaUrl && <a href={mediaUrl} target="_blank" rel="noreferrer">Mở nội dung media</a>}
    </aside>
  );
}
