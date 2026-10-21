"use client";

import type { CSSProperties } from "react";
import styles from "./TriptychCard.module.css";

export interface TriptychCardData {
  slug: string;
  title: string;
  description?: string | null;
  region?: string | null;
  duration_seconds?: number | null;
  voice_length?: number | null;
  card_image_url?: string | null;
  splash_image_url?: string | null;
  hover_video_url?: string | null;
  published?: string | null;
  language_label?: string | null;
  href?: string | null;
}

export interface TriptychCardProps {
  item: TriptychCardData;
  onInfo?: (slug: string) => void;
  exploreLabel?: string;
  infoLabel?: string;
  style?: CSSProperties;
}

function formatDuration(seconds?: number | null): string {
  if (!seconds || seconds <= 0) return "";
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  if (h > 0) return `${h} giờ ${m} phút`;
  return `${m} phút`;
}

export function TriptychCard({
  item,
  onInfo,
  exploreLabel = "Explore",
  infoLabel = "Info",
  style,
}: TriptychCardProps) {
  const { hover_video_url: video } = item;
  const hasVideo = Boolean(video);

  const meta = [
    item.published,
    formatDuration(item.duration_seconds),
    item.language_label,
  ].filter(Boolean);

  const videoClass = hasVideo ? styles.hp_triptych_card_has_video : "";

  return (
    <article
      className={[styles.hp_triptych_card, videoClass].filter(Boolean).join(" ")}
      style={style}
    >
      <div
        className={styles.hp_triptych_card_img}
        style={
          item.card_image_url
            ? { backgroundImage: `url(${item.card_image_url})` }
            : undefined
        }
      />

      {hasVideo ? (
        <video
          className={styles.hp_triptych_card_video}
          src={video || undefined}
          muted
          loop
          playsInline
          preload="metadata"
        />
      ) : null}

      <div className={styles.hp_triptych_card_overlay} />

      <div className={styles.hp_triptych_card_content}>
        <div className={styles.hp_triptych_card_text}>
          <div className={styles.hp_triptych_card_heading}>
            <h2 className={styles.hp_triptych_card_title}>
              <span className={styles.hp_triptych_card_title_full}>{item.title}</span>
              <span className={styles.hp_triptych_card_title_short}>{item.title}</span>
            </h2>
            {item.region ? (
              <div className={styles.hp_triptych_card_location}>{item.region}</div>
            ) : null}
          </div>

          <div className={styles.hp_triptych_card_details}>
            {meta.length > 0 ? (
              <div className={styles.hp_triptych_card_meta}>
                {meta.map((text, i) => (
                  <span key={i}>
                    {i > 0 && (
                      <span className={styles.hp_triptych_card_meta_sep}>·</span>
                    )}
                    {text}
                  </span>
                ))}
              </div>
            ) : null}

            {item.description ? (
              <p className={styles.hp_triptych_card_desc}>{item.description}</p>
            ) : null}

            <div className={styles.hp_triptych_card_buttons}>
              <a
                href={item.href || "#"}
                className={`${styles.hp_triptych_card_cta} ${styles.hp_triptych_card_explore_btn}`}
                target="_blank"
                rel="noopener"
              >
                {exploreLabel}
              </a>
              <button
                type="button"
                className={`${styles.hp_triptych_card_cta} ${styles.hp_triptych_card_info_btn} ${styles.hp_triptych_card_cta_secondary}`}
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
    </article>
  );
}

export default TriptychCard;