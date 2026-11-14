"use client";

import { useEffect, useId, useRef, useState } from "react";
import Image from "next/image";
import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { Alert, Button, ConfigProvider, Empty, Skeleton, theme } from "antd";
import PortraitCard, {
  type PortraitCardData,
} from "@/components/PortraitCard/PortraitCard";
import styles from "@/features/home/HeritageCarouselSection.module.css";

export interface HeritageItem extends PortraitCardData {
  backdropImageUrl?: string | null;
  kind?: "person";
  heritageTitle?: string;
}

export interface HeritageCarouselSectionProps {
  title: string;
  description?: string;
  items: HeritageItem[];
  sharedBackdrop?: boolean;
  loading?: boolean;
  error?: string;
  emptyMessage?: string;
  onRetry?: () => void;
  onCardClick?: (slug: string) => void;
  className?: string;
}

function PersonImage({ item }: { item: HeritageItem }) {
  const [failed, setFailed] = useState(false);

  return item.card_image_url && !failed ? (
    <Image
      src={item.card_image_url}
      alt=""
      width={220}
      height={330}
      sizes="(max-width: 640px) 170px, 220px"
      unoptimized
      loading="lazy"
      className={styles.personImage}
      onError={() => setFailed(true)}
    />
  ) : null;
}

function getBackdropImage(item: HeritageItem | undefined) {
  return item?.backdropImageUrl || item?.card_image_url || item?.hover_image_url;
}

export function HeritageCarouselSection({
  title,
  description,
  items,
  sharedBackdrop = false,
  loading = false,
  error,
  emptyMessage = "Chưa có nội dung.",
  onRetry,
  onCardClick,
  className,
}: HeritageCarouselSectionProps) {
  const titleId = useId();
  const listId = `${titleId}-list`;
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeImage, setActiveImage] = useState<string | null>(null);
  const [scrollable, setScrollable] = useState({ left: false, right: false });

  useEffect(() => { setActiveImage(null); }, [items]);

  useEffect(() => {
    const track = scrollRef.current;
    if (!track) return;
    const update = () => {
      const left = track.scrollLeft > 2;
      const right = track.scrollLeft + track.clientWidth < track.scrollWidth - 2;
      setScrollable((current) => current.left === left && current.right === right
        ? current : { left, right });
    };
    update();
    track.addEventListener("scroll", update, { passive: true });
    const observer = new ResizeObserver(update);
    observer.observe(track);
    return () => {
      track.removeEventListener("scroll", update);
      observer.disconnect();
    };
  }, [items, loading, error]);

  const scroll = (direction: -1 | 1) => {
    const track = scrollRef.current;
    const firstCard = track?.querySelector<HTMLElement>("[data-carousel-card]");
    if (!track || !firstCard) return;
    const style = window.getComputedStyle(track);
    const gap = parseFloat(style.columnGap) || 16;
    const step = firstCard.offsetWidth + gap;
    const width = track.clientWidth - parseFloat(style.paddingLeft)
      - parseFloat(style.paddingRight);
    const count = Math.max(1, Math.floor((width + gap) / step));
    track.scrollBy({
      left: direction * count * step,
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "auto" : "smooth",
    });
  };

  const backgroundImage = sharedBackdrop
    ? null
    : activeImage || getBackdropImage(items.find(getBackdropImage));
  const hasCards = items.length > 0;
  const showLoading = loading && !hasCards;

  return (
    <ConfigProvider theme={{
      algorithm: theme.darkAlgorithm,
      token: { colorPrimary: "#ff9b2d", fontFamily: "Poppins, sans-serif" },
    }}>
      <section
        className={[
          styles.carouselSection,
          sharedBackdrop && styles.transparentSection,
          className,
        ].filter(Boolean).join(" ")}
        aria-labelledby={titleId}
      >
        {!sharedBackdrop && (
          <div className={styles.sectionBackdrop} aria-hidden="true">
            {backgroundImage && (
              <div
                key={backgroundImage}
                className={styles.ambientImage}
                style={{ backgroundImage: `url(${JSON.stringify(backgroundImage)})` }}
              />
            )}
            <div className={styles.ambientFade} />
          </div>
        )}

        <div className={styles.sectionHeader}>
          <div className={styles.headerLeft}>
            <span className={styles.diamondIcon} aria-hidden="true">❖</span>
            <div>
              <h2 id={titleId} className={styles.sectionTitle}>{title}</h2>
              {description && <p className={styles.sectionDescription}>{description}</p>}
            </div>
          </div>
          <div className={styles.navButtons}>
            <Button
              shape="circle"
              className={styles.navButton}
              disabled={!hasCards || !scrollable.left}
              onClick={() => scroll(-1)}
              aria-label={`Cuộn trái danh mục ${title}`}
              aria-controls={listId}
              icon={<LeftOutlined aria-hidden="true" />}
            />
            <Button
              shape="circle"
              className={styles.navButton}
              disabled={!hasCards || !scrollable.right}
              onClick={() => scroll(1)}
              aria-label={`Cuộn phải danh mục ${title}`}
              aria-controls={listId}
              icon={<RightOutlined aria-hidden="true" />}
            />
          </div>
        </div>

        {error && hasCards && (
          <Alert
            className={styles.loadNotice}
            type="warning"
            showIcon
            title={error}
            action={onRetry && <Button size="small" onClick={onRetry}>Thử lại</Button>}
          />
        )}

        <div
          ref={scrollRef}
          id={listId}
          className={styles.scrollContainer}
          role="list"
          aria-label={title}
          aria-busy={showLoading}
        >
          {showLoading ? Array.from({ length: 8 }, (_, index) => (
            <div key={index} className={styles.cardSlot} aria-hidden="true">
              <Skeleton.Node active className={styles.cardSkeleton} />
            </div>
          )) : !hasCards && error ? (
            <div className={styles.statePanel}>
              <Alert
                type="warning"
                showIcon
                title="Chưa thể tải nội dung"
                description={error}
                action={onRetry && <Button onClick={onRetry}>Thử lại</Button>}
              />
            </div>
          ) : !hasCards ? (
            <div className={styles.statePanel} role="status">
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyMessage} />
            </div>
          ) : items.map((item) => (
            <div
              key={item.slug}
              className={styles.cardSlot}
              role="listitem"
              data-carousel-card
              onMouseEnter={sharedBackdrop
                ? undefined
                : () => setActiveImage(getBackdropImage(item) || null)}
              onFocus={sharedBackdrop
                ? undefined
                : () => setActiveImage(getBackdropImage(item) || null)}
            >
              {item.kind === "person" ? (
                <button
                  type="button"
                  className={styles.personCard}
                  onClick={() => onCardClick?.(item.slug)}
                  aria-haspopup="dialog"
                >
                  <PersonImage key={item.card_image_url || item.slug} item={item} />
                  <span className={styles.cardOverlay} />
                  <span className={styles.cardContent}>
                    <span className={styles.cardTitle}>{item.title}</span>
                    {item.region && <span className={styles.cardRegion}>{item.region}</span>}
                  </span>
                </button>
              ) : (
                <PortraitCard item={item} onInfo={onCardClick} className={styles.portraitCard} />
              )}
            </div>
          ))}
        </div>
      </section>
    </ConfigProvider>
  );
}

export default HeritageCarouselSection;
