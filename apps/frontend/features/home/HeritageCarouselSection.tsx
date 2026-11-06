"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { DotmSquare1 } from "@/components/ui/dotm-square-1";
import styles from "./HeritageCarouselSection.module.css";

export interface HeritageItem {
  slug: string;
  title: string;
  region?: string | null;
  card_image_url?: string | null;
  splash_image_url?: string | null;
  [key: string]: unknown;
}

export interface HeritageCarouselSectionProps {
  title: string;
  description?: string;
  items: HeritageItem[];
  onCardClick?: (slug: string) => void;
  className?: string;
}

function CardImage({ src, title, onReady }: { src: string; title: string; onReady: () => void }) {
  const frame = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    const element = frame.current;
    if (!element) return;
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        setVisible(true);
        observer.disconnect();
      }
    }, { rootMargin: "120px" });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={frame} className={styles.cardMedia} aria-busy={visible && status === "loading"}>
      {visible && status === "loading" && (
        <span className={styles.cardLoader} role="status" aria-label={`Đang tải ảnh ${title}`}>
          <DotmSquare1 size={32} dotSize={4} speed={1.2} bloom />
        </span>
      )}
      {visible && status !== "error" && (
        <Image src={src} alt={title} width={200} height={320} unoptimized
          className={`${styles.cardImage} ${status === "ready" ? styles.cardImageReady : ""}`}
          onLoad={() => { setStatus("ready"); onReady(); }}
          onError={() => setStatus("error")} />
      )}
      {status === "error" && <span className={styles.cardImageError}>Không tải được ảnh</span>}
    </div>
  );
}

/**
 * Diamond Icon SVG màu hổ phách (#FF6422)
 */
function DiamondIcon() {
  return (
    <svg
      className={styles.diamondIcon}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M12 2L2 12l10 10 10-10L12 2z" />
    </svg>
  );
}

export function HeritageCarouselSection({
  title,
  description,
  items,
  onCardClick,
  className,
}: HeritageCarouselSectionProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const [activeImageUrl, setActiveImageUrl] = useState<string | null>(null);

  useEffect(() => {
    setActiveImageUrl(null);
  }, [items]);

  const handleCardHover = (item: HeritageItem) => {
    const img = item.card_image_url || item.splash_image_url;
    if (img && img !== activeImageUrl) {
      setActiveImageUrl(img);
    }
  };

  const handleScroll = (direction: "left" | "right") => {
    if (scrollRef.current) {
      const scrollAmount = direction === "left" ? -440 : 440;
      scrollRef.current.scrollBy({ left: scrollAmount, behavior: "smooth" });
    }
  };

  // Chưa có dữ liệu (API đang tải hoặc lỗi) ⇒ không render section rỗng.
  if (items.length === 0) return null;

  return (
    <section
      className={[styles.carouselSection, className].filter(Boolean).join(" ")}
      aria-label={title}
    >
      {/* Khung nền mờ chuyển màu sâu (Cinematic Ambient Backdrop) */}
      <div className={styles.sectionBackdropContainer} aria-hidden="true">
        {/* 1. Ảnh nền mờ lấy theo thẻ đang chọn hoặc thẻ đầu tiên */}
        <div
          className={styles.ambientImageBlur}
          style={{
            backgroundImage: activeImageUrl ? `url(${activeImageUrl})` : undefined,
          }}
        />

        {/* 2. Quầng sáng màu xanh biển đặc trưng như Figma */}
        <div className={styles.ambientRadialGlow} />

        {/* 3. Lớp gradient tối chuyển tiếp giữa các section */}
        <div className={styles.ambientDarkFade} />
      </div>

      {/* Header danh mục (z-index: 2) */}
      <div className={styles.sectionHeader}>
        <div className={styles.headerLeft}>
          <div className={styles.titleRow}>
            <DiamondIcon />
            <h2 className={styles.sectionTitle}>{title}</h2>
          </div>
          {description ? (
            <p className={styles.sectionDescription}>{description}</p>
          ) : null}
        </div>

        {/* Cặp nút mũi tên tròn điều hướng < và > */}
        <div className={styles.navButtons}>
          <button
            type="button"
            className={styles.navButton}
            onClick={() => handleScroll("left")}
            aria-label={`Cuộn trái danh mục ${title}`}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
          <button
            type="button"
            className={styles.navButton}
            onClick={() => handleScroll("right")}
            aria-label={`Cuộn phải danh mục ${title}`}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        </div>
      </div>

      {/* Danh sách thẻ card cuộn ngang (z-index: 2) */}
      <div className={styles.scrollContainer} ref={scrollRef}>
        {items.map((item) => {
          const imageUrl =
            item.card_image_url ||
            item.splash_image_url ||
            "/images/featured-bg.jpg";

          return (
            <div
              key={item.slug}
              className={styles.card}
              onClick={() => onCardClick?.(item.slug)}
              onMouseEnter={() => handleCardHover(item)}
              onFocus={() => handleCardHover(item)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onCardClick?.(item.slug);
                }
              }}
            >
              <CardImage
                key={imageUrl}
                src={imageUrl}
                title={item.title}
                onReady={() => setActiveImageUrl((current) => current ?? imageUrl)}
              />
              <div className={styles.cardOverlay} />
              <div className={styles.cardContent}>
                <h3 className={styles.cardTitle}>{item.title}</h3>
                {item.region ? (
                  <p className={styles.cardRegion}>{item.region}</p>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default HeritageCarouselSection;
