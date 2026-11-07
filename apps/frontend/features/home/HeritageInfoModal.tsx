"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/Button/Button";
import type { HeritageItem } from "@/services/heritage.service";
import styles from "./HeritageInfoModal.module.css";

interface HeritageInfoModalProps {
  item: HeritageItem | null;
  onClose: () => void;
}

export const HeritageInfoModal: React.FC<HeritageInfoModalProps> = ({ item, onClose }) => {
  const router = useRouter();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!item) return null;

  const title = item.title || "Khám phá di sản";
  const location = item.region || "Việt Nam";
  const description = item.description || "";
  const slug = item.slug || "";
  const publishYear = item.publish_date ? new Date(item.publish_date).getFullYear() : new Date().getFullYear();
  const lang = item.language1?.name || "Tiếng Việt";

  // Lấy video hover nếu có
  const rawVideo = item.hover_video_url;
  const videoUrl = typeof rawVideo === "string" && rawVideo.trim().length > 0 ? rawVideo : null;
  const hasValidVideo = Boolean(videoUrl);

  // Lấy ảnh tĩnh splash
  const splashImg =
    item.splash_image_url ||
    item.card_image_url ||
    item.coverImage ||
    "https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?auto=format&fit=crop&w=1200&q=80";

  const displayVoices = item.voices && item.voices.length > 0 ? item.voices : [];

  const handleExplore = () => {
    onClose();
    if (slug) router.push(`/content/${slug}`);
  };

  const handleShare = async () => {
    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({
          title,
          text: description,
          url: window.location.href,
        });
      } catch {
        // Dismissed by user
      }
    } else if (typeof navigator !== "undefined") {
      void navigator.clipboard.writeText(window.location.href);
      alert("Đã sao chép liên kết vào clipboard!");
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose} role="dialog" aria-modal="true">
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Nền Media */}
        <div className={styles.mediaLayer}>
          {hasValidVideo && videoUrl ? (
            <video
              key={videoUrl}
              src={videoUrl}
              autoPlay
              loop
              muted
              playsInline
              poster={splashImg}
              className={styles.mediaElement}
            />
          ) : (
            <img src={splashImg} alt={title} className={styles.mediaElement} />
          )}

          <div className={styles.gradientOverlay} />
        </div>

        <button className={styles.closeButton} onClick={onClose} aria-label="Close modal">
          ✕
        </button>

        <div className={styles.contentContainer}>
          <div className={styles.headerBlock}>
            <h2 className={styles.title}>{title}</h2>
            <div className={styles.location}>{location}</div>
          </div>

          <div className={styles.metaBlock}>
            <span className={styles.badge}>Năm {publishYear}</span>
            <span className={styles.divider}>•</span>
            <span className={styles.aboutLink}>Giới thiệu</span>
            <span className={styles.divider}>•</span>
            <span className={styles.langText}>{lang}</span>
          </div>

          {description && (
            <div className={styles.descBlock}>
              <p className={styles.description}>{description}</p>
            </div>
          )}

          {displayVoices.length > 0 && (
            <div className={styles.contributorsBlock}>
              {displayVoices.slice(0, 3).map((voice, idx) => (
                <div key={voice.id || idx} className={styles.contributorItem}>
                  <img
                    src={
                      voice.headshot_url ||
                      "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&h=100&q=80"
                    }
                    alt={voice.name}
                    className={styles.avatar}
                  />
                  <div className={styles.contributorInfo}>
                    <span className={styles.contributorName}>{voice.name}</span>
                    <span className={styles.contributorRole}>{voice.title}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className={styles.actionsBlock}>
            <Button
              variant="primary"
              className={styles.customExploreBtn}
              onClick={handleExplore}
            >
              Khám phá
            </Button>

            <Button
              className={styles.customShareBtn}
              onClick={handleShare}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
                <polyline points="16 6 12 2 8 6" />
                <line x1="12" y1="2" x2="12" y2="15" />
              </svg>
              Chia sẻ
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
