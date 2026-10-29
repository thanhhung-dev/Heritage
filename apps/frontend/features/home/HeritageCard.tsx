'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import styles from './HeritageCard.module.css';

export interface HeritageItem {
  id?: string | number;
  slug?: string;
  name?: string;
  title?: string;
  region?: string;
  category?: string;
  imageUrl?: string;
  image?: string;
  routeType?: 'heritage' | 'content';
}

interface HeritageCardProps {
  item?: HeritageItem;
  isLoading?: boolean;
  onOpenModal?: (item: HeritageItem) => void;
}

const DEFAULT_FALLBACK_IMAGE =
  'https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?auto=format&fit=crop&w=600&q=80';

export default function HeritageCard({ item, isLoading = false, onOpenModal }: HeritageCardProps) {
  const [imgSrc, setImgSrc] = useState<string>(
    item?.imageUrl || item?.image || DEFAULT_FALLBACK_IMAGE
  );
  const [isImgLoading, setIsImgLoading] = useState<boolean>(true);

  // 1. Trạng thái Loading Skeleton cho Card
  if (isLoading || !item) {
    return (
      <div className={`${styles.cardContainer} ${styles.skeletonCard}`}>
        <div className={`${styles.imageWrapper} ${styles.skeletonPulse}`} />
        <div className={styles.content}>
          <div className={`${styles.skeletonLine} ${styles.skeletonTitle}`} />
          <div className={`${styles.skeletonLine} ${styles.skeletonSubtitle}`} />
        </div>
      </div>
    );
  }

  const displayTitle = item.name || item.title || 'Di tích';
  const itemSlug = item.slug || '';

  // 2. Định tuyến chuyển trang
  const targetHref =
    item.routeType === 'content'
      ? `/content/${itemSlug}`
      : `/heritage/${itemSlug}`;

  const handleClick = (e: React.MouseEvent) => {
    if (onOpenModal) {
      e.preventDefault();
      onOpenModal(item);
    }
  };

  return (
    <Link href={targetHref} className={styles.cardContainer} onClick={handleClick}>
      <div className={styles.imageWrapper}>
        <Image
          src={imgSrc}
          alt={displayTitle}
          fill
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
          className={`${styles.cardImage} ${isImgLoading ? styles.imgBlur : styles.imgLoaded}`}
          onLoad={() => setIsImgLoading(false)}
          onError={() => {
            if (imgSrc !== DEFAULT_FALLBACK_IMAGE) {
              setImgSrc(DEFAULT_FALLBACK_IMAGE);
            }
            setIsImgLoading(false);
          }}
        />
        {item.category && <span className={styles.badge}>{item.category}</span>}
      </div>

      <div className={styles.content}>
        <h3 className={styles.title}>{displayTitle}</h3>
        {item.region && (
          <div className={styles.regionWrapper}>
            <span className={styles.regionText}>{item.region}</span>
          </div>
        )}
      </div>
    </Link>
  );
}