"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/Button/Button";
import { HeritageItem } from "@/services/heritage.service";
import styles from "./HeritageInfoModal.module.css";

interface HeritageInfoModalProps {
  item: HeritageItem | null;
  onClose: () => void;
}

const MOCK_FALLBACK_VOICES = [
  {
    id: 901,
    name: "Ngọc Ngân",
    title: "Người thuyết minh tiếng Việt",
    headshot_url: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&h=100&q=80",
  },
  {
    id: 902,
    name: "Hung Heo",
    title: "Cultural Interpreter, Musician",
    headshot_url: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=100&h=100&q=80",
  },
  {
    id: 903,
    name: "Hung Heo",
    title: "Cultural Interpreter, Dancer",
    headshot_url: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=100&h=100&q=80",
  },
];

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

  const title = item.title || "Look Eye to Eye with the Towering Faces of Mount Rushmore";
  const location = item.region || "Keystone, South Dakota";
  const description =
    item.description ||
    "Explore Mount Rushmore National Memorial through the stories of the many communities whose cultural traditions have shaped this place and continue to flourish in the Black Hills.";
  const slug = item.slug || "";
  const publishYear = item.publish_date ? new Date(item.publish_date).getFullYear() : 2025;
  const lang = item.language1?.name || "English";

  // Lấy video hover
  const rawVideo = (item as any).hover_video_url;
  const isTuDuc = String(item.slug).includes("tu-duc") || String(item.title).toLowerCase().includes("tự đức");
  const videoUrl = rawVideo || (isTuDuc ? "/tuc-duc-hover.mp4" : null);
  const hasValidVideo = typeof videoUrl === "string" && videoUrl.trim().length > 0;

  // Lấy ảnh tĩnh splash
  const splashImg =
    item.splash_image_url ||
    item.card_image_url ||
    (item as any).coverImage ||
    "https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?auto=format&fit=crop&w=1200&q=80";

  let displayVoices = item.voices && item.voices.length > 0 ? [...item.voices] : [];
  if (displayVoices.length < 3) {
    const needed = 3 - displayVoices.length;
    displayVoices = [...displayVoices, ...MOCK_FALLBACK_VOICES.slice(3 - needed)];
  }

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
        // Dismissed
      }
    } else if (typeof navigator !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      alert("Đã sao chép liên kết vào clipboard!");
    }
  };

  return (
    <div className={styles.overlay} onClick={onClose} role="dialog" aria-modal="true">
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Nền Media */}
        <div className={styles.mediaLayer}>
          {hasValidVideo ? (
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
            <span className={styles.badge}>Published {publishYear}</span>
            <span className={styles.divider}>•</span>
            <span className={styles.aboutLink}>About</span>
            <span className={styles.divider}>•</span>
            <span className={styles.langText}>{lang}</span>
          </div>

          <div className={styles.descBlock}>
            <p className={styles.description}>{description}</p>
          </div>

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

          <div className={styles.actionsBlock}>
            <Button
              variant="primary"
              className={styles.customExploreBtn}
              onClick={handleExplore}
            >
              Explore
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
              Share
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};