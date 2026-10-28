'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import styles from './HeritageCard.module.css';

export interface HeritageItem {
  id: string | number;
  slug: string;
  name: string;
  region?: string;
  category?: string;
  imageUrl?: string;
 routeType?: 'heritage' | 'content'; // Linh hoạt điều hướng 2 router
}

interface HeritageCardProps {
  item: HeritageItem;
  onOpenModal?: (item: HeritageItem) => void; // Dành cho trường hợp mở modal chi tiết
}

export default function HeritageCard({ item, onOpenModal }: HeritageCardProps) {
  // Ảnh mặc định dự phòng nếu link ảnh bị lỗi hoặc 404
  const [imgSrc, setImgSrc] = useState(item.imageUrl || '/images/placeholder.jpg');

  // Xử lý route điều hướng: qua trang content hoặc trang heritage
  const targetHref = item.routeType === 'content'
    ? `/content/${item.slug}`
    : `/heritage/${item.slug}`;

  const handleClick = (e: React.MouseEvent) => {
    // Nếu có handler mở modal (trường hợp router modal) thì chặn redirect
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
          alt={item.name}
          fill
          sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          className={styles.cardImage}
          onError={() => {
            setImgSrc('/images/placeholder.jpg');
          }}
        />
        {item.category && (
          <span className={styles.badge}>{item.category}</span>
        )}
      </div>

      <div className={styles.content}>
        <h3 className={styles.title}>{item.name}</h3>
        {item.region && (
          <div className={styles.regionWrapper}>
            <span className={styles.regionText}>{item.region}</span>
          </div>
        )}
      </div>
    </Link>
  );
}