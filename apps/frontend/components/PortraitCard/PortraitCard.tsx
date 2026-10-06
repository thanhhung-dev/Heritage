"use client";

import type { CSSProperties } from "react";
import styles from "./portrait-card.module.css";

export interface PortraitCardData {
  slug: string;
  title: string;
  description?: string | null;
  region?: string | null;
  card_image_url?: string | null;
  hover_video_url?: string | null;
  hover_image_url?: string | null;
  published?: string | null;
  language_label?: string | null;
  href?: string | null;
}

export interface PortraitCardProps {
  item: PortraitCardData;
  onInfo?: (slug: string) => void;
  exploreLabel?: string;
  infoLabel?: string;
  style?: CSSProperties;
}

export function PortraitCard({
  item,
  onInfo,
  exploreLabel = "Explore",
  infoLabel = "Info",
  style,
}: PortraitCardProps) {
  const { hover_video_url: video, hover_image_url: hoverImage } = item;
  const hasVideo = Boolean(video);
  const hasHoverImg = Boolean(hoverImage);

  const meta = [item.published, item.language_label ?? "English"].filter(Boolean);

  const classNames = [
    styles.hp_portrait_card,
    hasVideo ? styles.hp_portrait_card_has_video : "",
    hasHoverImg ? styles.hp_portrait_card_has_hover_img : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <article className={classNames} style={style} data-card-id={item.slug}>
      <div className={styles.hp_portrait_card_img}>
        {item.card_image_url ? (
          <img
            src={item.card_image_url}
            alt={item.title}
            width={220}
            height={330}
            loading="lazy"
          />
        ) : null}
      </div>

      {hasVideo ? (
        <video
          className={styles.hp_portrait_card_video}
          src={video || undefined}
          muted
          loop
          playsInline
          preload="metadata"
        />
      ) : null}

      {hasHoverImg ? (
        <img
          className={styles.hp_portrait_card_hover_img}
          src={hoverImage || undefined}
          alt=""
          loading="lazy"
        />
      ) : null}

      <div className={styles.hp_portrait_card_overlay} />

      <div className={styles.hp_portrait_card_content}>
        <h3 className={styles.hp_portrait_card_title}>{item.title}</h3>

        {item.region ? (
          <div className={styles.hp_portrait_card_location}>{item.region}</div>
        ) : null}

        <div className={styles.hp_portrait_card_details}>
          {meta.length > 0 ? (
            <div className={styles.hp_portrait_card_meta}>
              {meta.map((text, i) => (
                <span key={i}>
                  {i > 0 && (
                    <span className={styles.hp_portrait_card_meta_sep}>·</span>
                  )}
                  {text}
                </span>
              ))}
            </div>
          ) : null}

          {item.description ? (
            <p className={styles.hp_portrait_card_desc}>{item.description}</p>
          ) : null}

          <div className={styles.hp_portrait_card_buttons}>
            <a
              href={item.href || "#"}
              className={`${styles.hp_portrait_card_cta} ${styles.hp_portrait_card_explore_btn}`}
              target="_blank"
              rel="noopener"
            >
              {exploreLabel}
            </a>
            <button
              type="button"
              className={`${styles.hp_portrait_card_cta} ${styles.hp_portrait_card_cta_secondary} ${styles.hp_portrait_card_info_btn}`}
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
    </article>
  );
}

export default PortraitCard;