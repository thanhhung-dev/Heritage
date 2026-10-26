'use client';

import React from 'react';
import styles from './HeritageDetailModal.module.css';

export interface HeritageItem {
  id: string;
  title: string;
  category: string;
  period?: string;
  description: string;
  imageUrl: string;
}

interface HeritageDetailModalProps {
  item: HeritageItem | null;
  isOpen: boolean;
  onClose: () => void;
  onNavigate?: (id: string) => void;
}

export const HeritageDetailModal: React.FC<HeritageDetailModalProps> = ({
  item,
  isOpen,
  onClose,
  onNavigate,
}) => {
  if (!isOpen || !item) return null;

  return (
    <div className={styles.backdrop} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <button className={styles.closeBtn} onClick={onClose} aria-label="Close modal">
          ✕
        </button>
        
        <div className={styles.imageContainer}>
          <img src={item.imageUrl} alt={item.title} className={styles.image} />
          <span className={styles.badge}>{item.category}</span>
        </div>

        <div className={styles.content}>
          <div className={styles.meta}>{item.period || 'Di sản văn hóa'}</div>
          <h2 className={styles.title}>{item.title}</h2>
          <p className={styles.description}>{item.description}</p>

          <div className={styles.actions}>
            <button className={styles.secondaryBtn} onClick={onClose}>
              Đóng
            </button>
            <button 
              className={styles.primaryBtn}
              onClick={() => onNavigate && onNavigate(item.id)}
            >
              Khám phá chi tiết →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};