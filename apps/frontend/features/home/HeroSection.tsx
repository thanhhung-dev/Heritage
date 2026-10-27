"use client";

import { useState, useMemo, type CSSProperties } from "react";
import TriptychCard, {
  type TriptychCardData,
} from "@/components/TriptychCard/TriptychCard";
import triptychStyles from "@/components/TriptychCard/TriptychCard.module.css";
import styles from "./HeroSection.module.css";

export interface HeroTileProps {
  eyebrow?: string;
  title?: React.ReactNode;
  description?: string;
  subDescription?: string;
  className?: string;
}

export function HeroTile({
  eyebrow,
  title,
  description = "Explore real places in 3D and discover the people and stories that bring them to life.",
  subDescription = "From ancient wonders to national parks and historic homes, step into a new kind of virtual experience with Tapestry.",
  className,
}: HeroTileProps) {
  const renderedTitle = title ?? (
    <>
      Every Place Has a <br /> Story
    </>
  );

  return (
    <div
      className={[styles.heroTile, styles.hp_hero_left, className]
        .filter(Boolean)
        .join(" ")}
    >
      <div className={styles.hp_hero_headline_area}>
        {eyebrow ? <p className={styles.heroTileEyebrow}>{eyebrow}</p> : null}
        <h1 className={`${styles.heroTitle} ${styles.hp_hero_h1}`}>
          {renderedTitle}
        </h1>
        {description ? (
          <p className={`${styles.heroDescription} ${styles.hp_hero_tagline}`}>
            {description}
          </p>
        ) : null}
        {subDescription ? (
          <p
            className={`${styles.heroSubDescription} ${styles.hp_hero_tagline}`}
          >
            {subDescription}
          </p>
        ) : null}
      </div>
    </div>
  );
}

export const herotile = HeroTile;

export interface HeroSectionProps {
  items?: TriptychCardData[];
  title?: React.ReactNode;
  description?: string;
  subDescription?: string;
  eyebrow?: string;
  onInfo?: (slug: string) => void;
  exploreLabel?: string;
  infoLabel?: string;
  className?: string;
}

const LOCAL_FALLBACK_IMAGE = "/images/cung-an-dinh.jpg";

/**
 * Ba di sản được ưu tiên lên hero, theo thứ tự. Chỉ là *thứ tự chọn* trong danh
 * sách lấy từ API — không kèm dữ liệu nào, để hero luôn phản ánh DB.
 */
export const FEATURED_HERO_SLUGS = [
  ["lang-tu-duc", "tu-duc-tomb"],
  ["cung-an-dinh", "an-dinh-palace"],
  ["ngu-hanh-son", "marble-mountains"],
] as const;

function getCardImageUrl(item?: TriptychCardData): string {
  if (!item) return LOCAL_FALLBACK_IMAGE;
  return item.splash_image_url || item.card_image_url || LOCAL_FALLBACK_IMAGE;
}

function selectFeaturedTriptychItems(
  sourceItems: TriptychCardData[]
): TriptychCardData[] {
  if (sourceItems.length === 0) {
    return [];
  }

  const picked: TriptychCardData[] = [];
  for (let i = 0; i < FEATURED_HERO_SLUGS.length; i++) {
    const slugCandidates = FEATURED_HERO_SLUGS[i];
    const matched = sourceItems.find((item) =>
      (slugCandidates as readonly string[]).includes(item.slug)
    );
    // Không khớp slug ưu tiên: chỉ lấy theo đúng thứ tự khi API trả về đúng 3 mục,
    // tránh gán nhầm di sản của vị trí khác.
    const item = matched ?? (sourceItems.length === 3 ? sourceItems[i] : undefined);
    if (!item) continue;
    picked.push({
      ...item,
      card_image_url: item.card_image_url || item.splash_image_url,
      splash_image_url: item.splash_image_url || item.card_image_url,
      href: item.href || `/content/${item.slug}`,
    });
  }

  return picked.slice(0, 3);
}

export function HeroSection({
  items,
  title,
  description,
  subDescription,
  eyebrow,
  onInfo,
  exploreLabel = "Explore",
  infoLabel = "Info",
  className,
}: HeroSectionProps) {
  // Thuần trình bày: danh sách do nơi gọi truyền vào (đã fetch từ API). Không tự
  // fetch và không có card mặc định — trước đây component tự gọi API rồi rơi về
  // `DEFAULT_HERO_ITEMS`, khiến hero hiện dữ liệu không đến từ DB.
  const displayItems = useMemo(
    () => selectFeaturedTriptychItems(items ?? []),
    [items]
  );

  const [activeBgIndex, setActiveBgIndex] = useState<number>(0);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const [isAnimating, setIsAnimating] = useState<boolean>(false);

  const handleCardActivate = (_item: TriptychCardData, index: number) => {
    setIsAnimating(true);
    setActiveIndex(index);
    setActiveBgIndex(index);
  };

  const handleMouseLeave = () => {
    setIsAnimating(true);
    setActiveIndex(null);
  };

  return (
    <section
      className={[
        styles.heroSection,
        styles.hp_hero_triptych,
        styles.hp_hero_ready,
        triptychStyles.hp_hero_triptych,
        triptychStyles.hp_hero_ready,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      aria-label="Heritage Hero"
    >
      {/* 1. Các lớp ảnh nền mờ (.hp_hero_bg_layer) chuyển mượt bằng opacity */}
      {displayItems.map((item, idx) => {
        const bgUrl = getCardImageUrl(item);
        const isCurrentBg = activeBgIndex === idx;
        return (
          <div
            key={`bg-${item.slug}-${idx}`}
            className={[
              styles.hp_hero_bg_layer,
              isCurrentBg ? styles.hp_hero_bg_layer_active : "",
              idx === 0 && !isAnimating ? styles.hp_hero_bg_layer_ssr : "",
            ]
              .filter(Boolean)
              .join(" ")}
            style={{
              backgroundImage: `url(${bgUrl || LOCAL_FALLBACK_IMAGE})`,
            }}
            aria-hidden="true"
          />
        );
      })}

      {/* 2. Lớp gradient phủ tối để làm nổi bật chữ */}
      <div className={styles.heroOverlayGradient} aria-hidden="true" />

      {/* Container nội dung (.hp_hero_content) */}
      <div
        className={[
          styles.heroLayout,
          styles.hp_hero_content,
          isAnimating ? triptychStyles.hp_triptych_animating : "",
        ]
          .filter(Boolean)
          .join(" ")}
      >
        {/* Cột bên trái: HeroTile (.hp_hero_left) */}
        <HeroTile
          eyebrow={eyebrow}
          title={title}
          description={description}
          subDescription={subDescription}
        />

        {/* Cột bên phải: Triptych Section (.hp_triptych). Ẩn khi chưa có dữ liệu
            để layout `--hp-tt-n: 0` không tạo ra khung rỗng. */}
        {displayItems.length > 0 ? (
          <section
            className={`${triptychStyles.hp_triptych} ${styles.heroTriptych}`}
            id="hp_triptych"
            aria-label="Featured Experiences"
            style={
              {
                "--hp-tt-n": displayItems.length,
              } as CSSProperties
            }
            onMouseLeave={handleMouseLeave}
          >
            {displayItems.map((item, idx) => (
              <TriptychCard
                key={`hero-${item.slug}-${idx}`}
                item={item}
                index={idx}
                cardId={`card-${idx + 1}`}
                isActive={activeIndex === idx}
                isCollapsed={activeIndex !== null && activeIndex !== idx}
                onMouseEnter={() => handleCardActivate(item, idx)}
                onFocus={() => handleCardActivate(item, idx)}
                onClick={() => handleCardActivate(item, idx)}
                exploreLabel={exploreLabel}
                infoLabel={infoLabel}
                onInfo={onInfo}
              />
            ))}
          </section>
        ) : null}
      </div>
    </section>
  );
}

export const HomeSection = HeroSection;
export default HeroSection;
