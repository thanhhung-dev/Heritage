"use client";

import type { HeritageInteractiveHighlight } from "@/types/heritage";
import styles from "../styles.module.css";

export default function HighlightPanel({ highlight, onClose }: {
  highlight: HeritageInteractiveHighlight | null;
  onClose: () => void;
}) {
  if (!highlight) return null;
  const mediaUrl = highlight.media_url && /^(https?:\/\/|\/(?!\/))/i.test(highlight.media_url) ? highlight.media_url : null;
  return (
    <aside className={styles.hotspotPopup} aria-labelledby="hotspot-popup-title">
      <button className={styles.hotspotPopupClose} type="button" aria-label="Close highlight" onClick={onClose}>&times;</button>
      <h2 id="hotspot-popup-title">{highlight.popup_title ?? "Highlight"}</h2>
      <p id="hotspot-popup-text">{highlight.popup_text}</p>
      {/* Schema hiện chỉ có media_url, chưa có MIME/type: không đoán ảnh/video từ đuôi URL. */}
      {mediaUrl && <a href={mediaUrl} target="_blank" rel="noreferrer">Mở nội dung media</a>}
    </aside>
  );
}
