"use client";

import { useState, useRef, type CSSProperties } from "react";
import Image from "next/image";
import Link from "next/link";
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
  community_made?: boolean | null;
  href?: string | null;
}

export interface PortraitCardProps {
  item: PortraitCardData;
  onInfo?: (slug: string) => void;
  exploreLabel?: string;
  infoLabel?: string;
  style?: CSSProperties;
  className?: string;
  variant?: "default" | "library";
}

export function PortraitCard({
  item,
  onInfo,
  exploreLabel = "Explore",
  infoLabel = "Info",
  style,
  className,
  variant = "default",
}: PortraitCardProps) {
  const [failedImage, setFailedImage] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  const { hover_video_url: video, hover_image_url: hoverImage } = item;
  const hasVideo = Boolean(video);
  const hasHoverImg = Boolean(hoverImage);

  const meta = [item.published, item.language_label ?? "English"].filter(Boolean);

  const handleMouseEnter = () => {
    if (hasVideo && videoRef.current) {
      const playPromise = videoRef.current.play();
      if (playPromise !== undefined) {
        playPromise.catch(() => {
          // Ignore autoplay interruptions on rapid hover
        });
      }
    }
  };

  const handleMouseLeave = () => {
    if (hasVideo && videoRef.current) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
  };

  const classNames = [
    styles.hp_portrait_card,
    "hp_portrait_card",
    hasVideo ? styles.hp_portrait_card_has_video : "",
    hasHoverImg ? styles.hp_portrait_card_has_hover_img : "",
    variant === "library" ? styles.library_card : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const cardImage =
    item.card_image_url && item.card_image_url !== failedImage
      ? item.card_image_url
      : null;
  const targetHref = item.href || `/content/${encodeURIComponent(item.slug)}`;

  return (
    <article
      className={classNames}
      style={style}
      data-card-id={item.slug}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className={styles.hp_portrait_card_img}>
        {cardImage ? (
          <Image
            src={cardImage}
            alt={item.title}
            width={220}
            height={330}
            sizes="(max-width: 480px) 50vw, (max-width: 1024px) 33vw, 220px"
            unoptimized
            loading="lazy"
            onError={() => setFailedImage(cardImage)}
          />
        ) : null}
      </div>

      {hasVideo ? (
        <video
          ref={videoRef}
          className={styles.hp_portrait_card_video}
          src={video || undefined}
          muted
          loop
          playsInline
          preload="metadata"
        />
      ) : null}

      {hoverImage ? (
        <Image
          className={styles.hp_portrait_card_hover_img}
          src={hoverImage}
          alt=""
          width={220}
          height={330}
          sizes="220px"
          unoptimized
          loading="lazy"
        />
      ) : null}

      {item.community_made ? (
        <div
          className={styles.tapestryCard_ComMade}
          id="tapestryCard_ComMade"
          aria-label="Community-made virtual tour"
        >
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
          </svg>
          <div className={styles.t_cm_hover} data-nosnippet="">
            Community-made virtual tours are created in collaboration with local
            stakeholders and community members who capture 3D data, record
            interviews, and design the narrative.
          </div>
        </div>
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
                  {i === 0 ? (
                    <span className={styles.hp_portrait_card_meta_date}>
                      {text}
                    </span>
                  ) : (
                    <span>{text}</span>
                  )}
                </span>
              ))}
            </div>
          ) : null}

          {item.description ? (
            <p className={styles.hp_portrait_card_desc}>{item.description}</p>
          ) : null}

          <div className={styles.hp_portrait_card_buttons}>
            <Link
              href={targetHref}
              className={`${styles.hp_portrait_card_cta} ${styles.hp_portrait_card_explore_btn}`}
            >
              {exploreLabel}
            </Link>
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
