"use client";

import Image from "next/image";
import { useEffect, useRef, useState, type MouseEvent } from "react";
import type { HeritageInteractiveHighlight } from "@/types/heritage";
import styles from "../styles.module.css";

const ICONS = "https://tapestry-storage-a0fkf0afgte8hndt.z01.azurefd.net/ui-elements/icons";
const safeUrl = (url?: string | null) => url && /^(https?:\/\/|\/(?!\/))/i.test(url) ? url : null;
/** Nhịp gợi ý panel đang thu gọn (khớp `@keyframes nudgeLeft`). */
const NUDGE_INTERVAL_MS = 10_000;

/**
 * Panel điểm tương tác (hotspot) — dựng theo đúng cấu trúc + CSS của panel gốc:
 *
 *   playpenInfoParent
 *   ├─ nút thu gọn (2 icon in/out, nằm NGOÀI panel ở `left: -48px`)
 *   ├─ nút đóng (viên kính tròn, góc trên trái panel)
 *   ├─ tiêu đề
 *   ├─ playpenInfoInner        ← vùng CUỘN
 *   │  ├─ nhóm ảnh (icon mở rộng chỉ hiện khi hover)
 *   │  ├─ video
 *   │  ├─ thanh tiến trình media (bấm để tua)
 *   │  ├─ audio
 *   │  ├─ nhóm mô tả (mô tả clamp 7 dòng + credit)
 *   │  └─ nhóm nút Read More / Read Less
 *   └─ orbTracker              ← ghim tuyệt đối ở đáy panel, ngoài vùng cuộn
 */
export default function HighlightPanel({ highlight, highlights = [], onClose }: {
  highlight: HeritageInteractiveHighlight | null;
  highlights?: HeritageInteractiveHighlight[];
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const descriptionRef = useRef<HTMLParagraphElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [nudge, setNudge] = useState(false);
  const [expandedImage, setExpandedImage] = useState(false);
  const [readMore, setReadMore] = useState(false);
  const [canReadMore, setCanReadMore] = useState(false);
  const [failedMediaUrl, setFailedMediaUrl] = useState<string | null>(null);
  const [failedAudioUrl, setFailedAudioUrl] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [visited, setVisited] = useState<number[]>([]);
  const highlightId = highlight?.id;
  useEffect(() => {
    if (highlightId === undefined) return;
    setCollapsed(false);
    setExpandedImage(false);
    setReadMore(false);
    setProgress(0);
    setFailedMediaUrl(null);
    setFailedAudioUrl(null);
    setVisited((previous) => previous.includes(highlightId) ? previous : [...previous, highlightId]);
    const active = document.activeElement;
    if (active instanceof HTMLElement && active !== closeRef.current) returnFocus.current = active;
    const frame = requestAnimationFrame(() => closeRef.current?.focus());
    const video = videoRef.current;
    const audio = audioRef.current;
    return () => { cancelAnimationFrame(frame); video?.pause(); audio?.pause(); };
  }, [highlightId]);
  useEffect(() => {
    if (!collapsed) { setNudge(false); return; }
    const id = window.setInterval(() => {
      setNudge(true);
      window.setTimeout(() => setNudge(false), 600);
    }, NUDGE_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [collapsed]);
  useEffect(() => {
    const description = descriptionRef.current;
    if (!description || collapsed || readMore) return;
    const measure = () => setCanReadMore(description.scrollHeight > description.clientHeight + 1);
    const observer = new ResizeObserver(measure);
    observer.observe(description);
    measure();
    return () => observer.disconnect();
  }, [highlightId, collapsed, readMore]);
  useEffect(() => {
    if (expandedImage) dialogRef.current?.showModal();
  }, [expandedImage]);
  const close = () => {
    const trigger = returnFocus.current;
    onClose();
    requestAnimationFrame(() => trigger?.focus());
  };
  const trackProgress = (media: HTMLMediaElement | null) => {
    if (!media || !Number.isFinite(media.duration) || media.duration <= 0) { setProgress(0); return; }
    setProgress(Math.min(1, media.currentTime / media.duration));
  };
  const seek = (event: MouseEvent<HTMLDivElement>) => {
    const media = videoRef.current ?? audioRef.current;
    if (!media || !Number.isFinite(media.duration) || media.duration <= 0) return;
    const rect = event.currentTarget.getBoundingClientRect();
    if (rect.width <= 0) return;
    const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    media.currentTime = ratio * media.duration;
    setProgress(ratio);
  };
  if (!highlight) return null;
  const mediaUrl = safeUrl(highlight.media_url);
  const audioUrl = safeUrl(highlight.audio_url);
  const captionsUrl = safeUrl(highlight.captions_url);
  const mediaFailed = mediaUrl !== null && mediaUrl === failedMediaUrl;
  const supportedMedia = highlight.media_type === "image" || highlight.media_type === "video";
  const title = highlight.popup_title ?? "Highlight";
  const viewedCount = highlights.filter((item) => visited.includes(item.id)).length;
  const showTracker = highlights.length > 0;
  const allFound = showTracker && viewedCount === highlights.length;
  const showVideo = !!mediaUrl && !mediaFailed && highlight.media_type === "video";
  const showAudio = !!audioUrl && failedAudioUrl !== audioUrl;
  return (
    <aside id="hotspot-popup" className={`${styles.hotspotPopup} ${styles.playpenInfoParent} ${collapsed ? `${styles.collapsed}${nudge ? ` ${styles.nudge}` : ""}` : ""}`}
      data-collapsed={collapsed} aria-labelledby="hotspot-popup-title"
      onKeyDown={(event) => { if (event.key === "Escape") { event.stopPropagation(); close(); } }}>
      <button id="playpenInfoCollapse" className={styles.infoCollapse} type="button"
        aria-label={collapsed ? "Expand info panel" : "Collapse info panel"}
        aria-expanded={!collapsed} aria-controls="playpenInfoInner" onClick={() => {
          videoRef.current?.pause(); audioRef.current?.pause(); setCollapsed(!collapsed);
        }}>
        <Image className={`${styles.infoCollapseIcon} ${styles.collapseIn}`} src={`${ICONS}/icon_collapse_in.svg`} alt="" width={40} height={40} unoptimized />
        <Image className={`${styles.infoCollapseIcon} ${styles.collapseOut}`} src={`${ICONS}/icon_collapse_out.svg`} alt="" width={40} height={40} unoptimized />
      </button>
      
      <h2 id="hotspot-popup-title" className={styles["playpenInfo-Title"]} hidden={collapsed}>{title}</h2>
      <div id="playpenInfoInner" className={styles.infoInner} hidden={collapsed}>
        {mediaUrl && !mediaFailed && highlight.media_type === "image" && (
          <div id="playpenInfo-ImgGroup" className={styles.infoImgGroup}>
            <button className={styles.infoImageButton} type="button" aria-label="Expand image" onClick={() => setExpandedImage(true)}>
              <Image id="playpenInfo-Img" className={`${styles.hotspotPopupMedia} ${styles["playpenInfo-Img"]}`} src={mediaUrl}
                alt={highlight.media_alt ?? title} width={250} height={180} sizes="420px" unoptimized onError={() => setFailedMediaUrl(mediaUrl)} />
              <Image className={styles.infoExpandIcon} src={`${ICONS}/icon_expand.svg`} alt="" width={32} height={32} unoptimized />
            </button>
          </div>
        )}
        {showVideo && (
          <video key={highlight.id} ref={videoRef} id="playpenInfo-Vid" className={`${styles.hotspotPopupMedia} ${styles["playpenInfo-Vid"]}`}
            src={mediaUrl} controls playsInline preload="metadata" crossOrigin="anonymous" aria-label={title}
            onPlay={() => audioRef.current?.pause()} onError={() => setFailedMediaUrl(mediaUrl)}
            onTimeUpdate={(event) => trackProgress(event.currentTarget)}
            onLoadedMetadata={(event) => trackProgress(event.currentTarget)}>
            {captionsUrl && <track kind="captions" label="English" srcLang="en" src={captionsUrl} default />}
          </video>
        )}
        {mediaUrl && (mediaFailed || !supportedMedia) && <>
          {mediaFailed && <p role="status">Không tải được media.</p>}
          <a href={mediaUrl} target="_blank" rel="noreferrer">Mở nội dung media</a>
        </>}
        {(showVideo || showAudio) && (
          <div id="playpenInfo-progressBar" className={styles.infoProgressBar}>
            <div className={styles.infoProgressFilled} onClick={seek} role="presentation" />
            <div className={styles.infoProgressFill} style={{ width: `${progress * 100}%` }} />
          </div>
        )}
        {audioUrl && (failedAudioUrl === audioUrl ? <>
          <p role="status">Không tải được audio.</p><a href={audioUrl} target="_blank" rel="noreferrer">Mở audio</a>
        </> : <audio key={`${highlight.id}-audio`} ref={audioRef} id="audioHighlight" src={audioUrl} controls preload="metadata"
          aria-label={`Audio: ${title}`} onPlay={() => videoRef.current?.pause()} onError={() => setFailedAudioUrl(audioUrl)}
          onTimeUpdate={(event) => trackProgress(event.currentTarget)}
          onLoadedMetadata={(event) => trackProgress(event.currentTarget)} />)}
        <div id="playpenInfo-DescGroup" className={styles.infoDescGroup}>
          <p ref={descriptionRef} id="hotspot-popup-text" className={styles["playpenInfo-Desc"]}>{highlight.popup_text}</p>
          {highlight.media_credit && <div id="playpenInfo-credit" className={styles.infoCredit}>{highlight.media_credit}</div>}
        </div>
        {(canReadMore || readMore) && (
          <div id="playpenInfo-DescButtonGroup" className={styles.infoDescButtons}>
            <button type="button" className={`${styles.infoReadMore} ${readMore ? styles.infoButtonHidden : ""}`}
              aria-expanded={readMore} aria-controls="hotspot-popup-text" onClick={() => setReadMore(true)}>Read More</button>
            <button type="button" className={`${styles.infoReadMore} ${styles.infoReadLess} ${readMore ? "" : styles.infoButtonHidden}`}
              aria-expanded={readMore} aria-controls="hotspot-popup-text" onClick={() => setReadMore(false)}>Read Less</button>
          </div>
        )}
      </div>
      {showTracker && <div id="orbTracker" className={styles.infoTracker} aria-label="Points discovered">
        <div className={styles["orbTracker-circles"]} aria-hidden="true">{highlights.map((item) => <span key={item.id}
          className={`${styles["orbTracker-circle"]} ${visited.includes(item.id) ? styles.orbVisited : ""}`} />)}</div>
        <div className={styles["orbTracker-count"]} role="status">{viewedCount}/{highlights.length}</div>
        {allFound && <div className={styles["orbTracker-allfound"]}>ALL FOUND</div>}
      </div>}
      {expandedImage && mediaUrl && <dialog ref={dialogRef} className={styles.infoImageDialog} aria-label={title}
        onCancel={() => setExpandedImage(false)} onKeyDown={(event) => event.stopPropagation()}>
        <button type="button" aria-label="Close expanded image" onClick={() => setExpandedImage(false)} autoFocus>&times;</button>
        <Image src={mediaUrl} alt={highlight.media_alt ?? title} width={1600} height={1200} sizes="90vw" unoptimized />
      </dialog>}
    </aside>
  );
}
