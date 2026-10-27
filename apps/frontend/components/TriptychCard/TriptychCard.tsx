"use client";

import { Fragment, useEffect, useRef, useState, type CSSProperties } from "react";
import styles from "./TriptychCard.module.css";

export interface TriptychLanguage {
  code?: string;
  name?: string;
}

export interface TriptychCardData {
  id?: number | string;
  slug: string;
  title: string;
  title_short?: string | null;
  description?: string | null;
  region?: string | null;
  duration_seconds?: number | null;
  voice_length?: number | null;
  card_image_url?: string | null;
  splash_image_url?: string | null;
  hover_video_url?: string | null;
  published?: string | null;
  publish_date?: string | null;
  language_label?: string | null;
  language1?: TriptychLanguage | null;
  language2?: TriptychLanguage | null;
  href?: string | null;
}

export interface TriptychCardProps {
  item: TriptychCardData;
  index?: number;
  cardId?: string;
  isActive?: boolean;
  isCollapsed?: boolean;
  onMouseEnter?: () => void;
  onFocus?: () => void;
  onClick?: () => void;
  onInfo?: (slug: string) => void;
  exploreLabel?: string;
  infoLabel?: string;
  style?: CSSProperties;
}

function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength).trimEnd()}…`;
}

export function TriptychCard({
  item,
  index = 0,
  cardId,
  isActive = false,
  isCollapsed = false,
  onMouseEnter,
  onFocus,
  onClick,
  onInfo,
  exploreLabel = "Explore",
  infoLabel = "Info",
  style,
}: TriptychCardProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [isVideoPlaying, setIsVideoPlaying] = useState(false);

  const video = item.hover_video_url;
  const hasVideo = Boolean(video);

  useEffect(() => {
    const videoEl = videoRef.current;
    if (!videoEl || !hasVideo) return;

    if (isActive) {
      const playPromise = videoEl.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            setIsVideoPlaying(true);
          })
          .catch(() => {
            setIsVideoPlaying(false);
          });
      }
    } else {
      videoEl.pause();
      videoEl.currentTime = 0;
      setIsVideoPlaying(false);
    }
  }, [isActive, hasVideo]);

  const publishedText =
    item.published ||
    (item.publish_date ? `Published ${item.publish_date.slice(0, 4)}` : null);

  const languageText =
    item.language_label ||
    [item.language1?.name, item.language2?.name].filter(Boolean).join(", ") ||
    null;

  const meta = [publishedText, languageText].filter((v): v is string =>
    Boolean(v)
  );

  const shortTitle = item.title_short || truncateText(item.title, 30);
  const shortDesc = item.description
    ? truncateText(item.description, 100)
    : null;
  const exploreHref = item.href || `/content/${item.slug}`;
  const cardImage =
    item.card_image_url || item.splash_image_url || "/images/cung-an-dinh.jpg";

  const cardClasses = [
    styles.hp_triptych_card,
    hasVideo ? styles.hp_triptych_card_has_video : "",
    isActive ? styles.hp_triptych_card_active : "",
    isCollapsed ? styles.hp_triptych_card_collapsed : "",
    isVideoPlaying ? styles.hp_triptych_card_video_playing : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className={cardClasses}
      data-index={index}
      data-card-id={cardId ?? `card-${index + 1}`}
      style={style}
      onMouseEnter={onMouseEnter}
      onFocus={onFocus}
      onClick={onClick}
    >
      <div
        className={styles.hp_triptych_card_img}
        style={{ backgroundImage: `url(${cardImage})` }}
      />

      {hasVideo ? (
        <video
          ref={videoRef}
          className={styles.hp_triptych_card_video}
          data-src={video || undefined}
          src={video || undefined}
          muted
          loop
          playsInline
          preload="metadata"
          onPlaying={() => setIsVideoPlaying(true)}
          onPause={() => setIsVideoPlaying(false)}
        />
      ) : null}

      <div className={styles.hp_triptych_card_overlay} />

      <div className={styles.hp_triptych_card_content}>
        <div className={styles.hp_triptych_card_text}>
          <div className={styles.hp_triptych_card_heading}>
            <h2 className={styles.hp_triptych_card_title}>
              <span className={styles.hp_triptych_card_title_full}>
                {item.title}
              </span>
              <span className={styles.hp_triptych_card_title_short}>
                {shortTitle}
              </span>
            </h2>
            {item.region ? (
              <div className={styles.hp_triptych_card_location}>
                {item.region}
              </div>
            ) : null}
          </div>

          <div className={styles.hp_triptych_card_details}>
            {meta.length > 0 ? (
              <div className={styles.hp_triptych_card_meta}>
                {meta.map((text, i) => (
                  <Fragment key={i}>
                    {i > 0 ? (
                      <span className={styles.hp_triptych_card_meta_sep}>·</span>
                    ) : null}
                    <span>{text}</span>
                  </Fragment>
                ))}
              </div>
            ) : null}

            {shortDesc ? (
              <p className={styles.hp_triptych_card_desc}>{shortDesc}</p>
            ) : null}

            <div className={styles.hp_triptych_card_buttons}>
              <a
                href={exploreHref}
                className={`${styles.hp_triptych_card_cta} ${styles.hp_triptych_card_explore_btn}`}
                target="_blank"
                rel="noopener"
                onClick={(e) => e.stopPropagation()}
              >
                {exploreLabel}
              </a>
              <button
                type="button"
                className={`${styles.hp_triptych_card_cta} ${styles.hp_triptych_card_cta_secondary} ${styles.hp_triptych_card_info_btn}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onInfo?.(item.slug);
                }}
              >
                {infoLabel}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TriptychCard;
