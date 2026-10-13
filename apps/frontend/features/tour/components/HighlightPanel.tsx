"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import type { HeritageInteractiveHighlight } from "@/types/heritage";
import styles from "../styles.module.css";

const ICONS = "https://tapestry-storage-a0fkf0afgte8hndt.z01.azurefd.net/ui-elements/icons";
const safeUrl = (url?: string | null) => url && /^(https?:\/\/|\/(?!\/))/i.test(url) ? url : null;

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
  const [expandedImage, setExpandedImage] = useState(false);
  const [readMore, setReadMore] = useState(false);
  const [canReadMore, setCanReadMore] = useState(false);
  const [failedMediaUrl, setFailedMediaUrl] = useState<string | null>(null);
  const [failedAudioUrl, setFailedAudioUrl] = useState<string | null>(null);
  const [visited, setVisited] = useState<number[]>([]);
  const highlightId = highlight?.id;
  useEffect(() => {
    if (highlightId === undefined) return;
    setCollapsed(false);
    setExpandedImage(false);
    setReadMore(false);
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
    // Đợi popup đóng để panel điểm tương tác trên màn hình thấp hiện lại.
    requestAnimationFrame(() => trigger?.focus());
  };
  if (!highlight) return null;
  const mediaUrl = safeUrl(highlight.media_url);
  const audioUrl = safeUrl(highlight.audio_url);
  const captionsUrl = safeUrl(highlight.captions_url);
  const mediaFailed = mediaUrl !== null && mediaUrl === failedMediaUrl;
  const supportedMedia = highlight.media_type === "image" || highlight.media_type === "video";
  const title = highlight.popup_title ?? "Highlight";
  const viewedCount = highlights.filter((item) => visited.includes(item.id)).length;
  return (
    <aside id="hotspot-popup" className={`${styles.hotspotPopup} ${styles.playpenInfoParent} ${collapsed ? styles.collapsed : ""}`} data-collapsed={collapsed}
      aria-labelledby="hotspot-popup-title"
      onKeyDown={(event) => { if (event.key === "Escape") { event.stopPropagation(); close(); } }}>
      <button className={styles.infoCollapse} type="button" aria-label={collapsed ? "Expand info panel" : "Collapse info panel"}
        aria-expanded={!collapsed} aria-controls="playpenInfoInner" onClick={() => {
          videoRef.current?.pause(); audioRef.current?.pause(); setCollapsed(!collapsed);
        }}>
        <Image src={`${ICONS}/icon_collapse_${collapsed ? "out" : "in"}.svg`} alt="" width={24} height={24} unoptimized />
      </button>
      <button ref={closeRef} hidden={collapsed} className={styles.hotspotPopupClose} type="button" aria-label="Close highlight" onClick={close}>&times;</button>
      <h2 id="hotspot-popup-title" className={styles["playpenInfo-Title"]} hidden={collapsed}>{title}</h2>
      <div id="playpenInfoInner" className={styles.infoInner} hidden={collapsed}>
        {mediaUrl && !mediaFailed && highlight.media_type === "image" && (
          <button className={styles.infoImageButton} type="button" aria-label="Expand image" onClick={() => setExpandedImage(true)}>
            <Image id="playpenInfo-Img" className={styles.hotspotPopupMedia} src={mediaUrl} alt={highlight.media_alt ?? title}
              width={250} height={180} sizes="320px" unoptimized onError={() => setFailedMediaUrl(mediaUrl)} />
            <Image className={styles.infoExpandIcon} src={`${ICONS}/icon_expand.svg`} alt="" width={22} height={22} unoptimized />
          </button>
        )}
        {mediaUrl && !mediaFailed && highlight.media_type === "video" && (
          <video key={highlight.id} ref={videoRef} id="playpenInfo-Vid" className={styles.hotspotPopupMedia} src={mediaUrl} controls playsInline
            preload="metadata" crossOrigin="anonymous" aria-label={title} onPlay={() => audioRef.current?.pause()} onError={() => setFailedMediaUrl(mediaUrl)}>
            {captionsUrl && <track kind="captions" label="English" srcLang="en" src={captionsUrl} default />}
          </video>
        )}
        {mediaUrl && (mediaFailed || !supportedMedia) && <>
          {mediaFailed && <p role="status">Không tải được media.</p>}
          <a href={mediaUrl} target="_blank" rel="noreferrer">Mở nội dung media</a>
        </>}
        {audioUrl && (failedAudioUrl === audioUrl ? <>
          <p role="status">Không tải được audio.</p><a href={audioUrl} target="_blank" rel="noreferrer">Mở audio</a>
        </> : <audio key={`${highlight.id}-audio`} ref={audioRef} id="audioHighlight" src={audioUrl} controls preload="metadata"
          aria-label={`Audio: ${title}`} onPlay={() => videoRef.current?.pause()} onError={() => setFailedAudioUrl(audioUrl)} />)}
        <p ref={descriptionRef} id="hotspot-popup-text" className={readMore ? undefined : styles.infoDescription}>{highlight.popup_text}</p>
        {highlight.media_credit && <p className={styles.infoCredit}>{highlight.media_credit}</p>}
        {(canReadMore || readMore) && <button className={styles.infoReadMore} type="button"
          aria-expanded={readMore} aria-controls="hotspot-popup-text" onClick={() => setReadMore(!readMore)}>{readMore ? "Read Less" : "Read More"}</button>}
        {highlights.length > 0 && <div id="orbTracker" className={styles.infoTracker} aria-label="Points discovered">
          <div className={styles["orbTracker-circles"]} aria-hidden="true">{highlights.map((item) => <span key={item.id}
            className={`${styles["orbTracker-circle"]} ${visited.includes(item.id) ? styles.visited : ""}`} />)}</div>
          <span role="status">{viewedCount}/{highlights.length}{viewedCount === highlights.length ? " — ALL FOUND" : ""}</span>
        </div>}
      </div>
      {expandedImage && mediaUrl && <dialog ref={dialogRef} className={styles.infoImageDialog} aria-label={title}
        onCancel={() => setExpandedImage(false)} onKeyDown={(event) => event.stopPropagation()}>
        <button type="button" aria-label="Close expanded image" onClick={() => setExpandedImage(false)} autoFocus>&times;</button>
        <Image src={mediaUrl} alt={highlight.media_alt ?? title} width={1600} height={1200} sizes="90vw" unoptimized />
      </dialog>}
    </aside>
  );
}
