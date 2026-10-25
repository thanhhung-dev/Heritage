"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRightOutlined, ClockCircleOutlined, EnvironmentOutlined, PictureOutlined } from "@ant-design/icons";
import { useState } from "react";
import type { HeritageSearchItem } from "./types";
import styles from "./search.module.css";

export function HeritageResultCard({ item }: { item: HeritageSearchItem }) {
  const [imageFailed, setImageFailed] = useState(false);
  const minutes = item.duration_seconds ? Math.max(1, Math.round(item.duration_seconds / 60)) : null;
  // Match existing heritage cards: load API-provided asset hosts directly.
  const imageUrl = item.card_image_url && /^(https?:\/\/|\/(?!\/))/.test(item.card_image_url) ? item.card_image_url : null;
  return (
    <article className={styles.card}>
      <Link className={styles.cardLink} href={`/content/${encodeURIComponent(item.slug)}`}>
        <div className={styles.cardImage}>
          {imageUrl && !imageFailed ? (
            <Image
              src={imageUrl}
              alt=""
              fill
              unoptimized
              sizes="(max-width: 600px) 100vw, (max-width: 1000px) 50vw, 33vw"
              onError={() => setImageFailed(true)}
            />
          ) : (
            <PictureOutlined className={styles.imagePlaceholder} aria-hidden />
          )}
          {item.category && <span className={styles.categoryBadge}>{item.category}</span>}
        </div>
        <div className={styles.cardBody}>
          {item.region && <p className={styles.cardRegion}><EnvironmentOutlined aria-hidden />{item.region}</p>}
          <h3>{item.title}</h3>
          <p className={styles.cardDescription}>{item.description || item.tagline || "Khám phá câu chuyện và không gian của di sản này."}</p>
          <div className={styles.cardFooter}>
            <span>{minutes && <><ClockCircleOutlined aria-hidden /> {minutes} phút</>}</span>
            <span className={styles.exploreLink}>Khám phá <ArrowRightOutlined aria-hidden /></span>
          </div>
        </div>
      </Link>
    </article>
  );
}
