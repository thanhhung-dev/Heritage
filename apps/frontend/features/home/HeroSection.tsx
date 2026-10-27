"use client";

import { useEffect, useState, useMemo, type CSSProperties } from "react";
import TriptychCard, {
  type TriptychCardData,
} from "@/components/TriptychCard/TriptychCard";
import triptychStyles from "@/components/TriptychCard/TriptychCard.module.css";
import { fetchHeritages } from "@/lib/heritage";
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

export const FEATURED_HERO_SLUGS = [
  ["lang-tu-duc", "tu-duc-tomb"],
  ["cung-an-dinh", "an-dinh-palace"],
  ["ngu-hanh-son", "marble-mountains"],
] as const;

export const DEFAULT_HERO_ITEMS: TriptychCardData[] = [
  {
    id: 1,
    slug: "lang-tu-duc",
    title: "Lăng Tự Đức",
    region: "Huế",
    publish_date: "2026-10-26",
    description:
      "Khám phá Khiêm Lăng, công trình gắn liền với vua Tự Đức, thông qua không gian 3D, văn bia Khiêm Cung Ký và khu lăng mộ.",
    hover_video_url:
      "https://pub-2fc54e5237344dc9b845f2ff2c9309f8.r2.dev/storage/TuDuc/tuc-duc-hover.mp4",
    splash_image_url:
      "https://pub-2fc54e5237344dc9b845f2ff2c9309f8.r2.dev/storage/TuDuc/splash-tu-duc.jpg",
    card_image_url:
      "https://pub-2fc54e5237344dc9b845f2ff2c9309f8.r2.dev/storage/TuDuc/card-tu-duc.jpg",
    language1: { code: "vi", name: "Vietnamese" },
    language2: { code: "en", name: "English" },
    href: "/content/lang-tu-duc",
  },
  {
    id: 5,
    slug: "cung-an-dinh",
    title: "Cung An Định",
    region: "Huế",
    publish_date: "2026-10-26",
    description:
      "Cung An Định được vua Khải Định cho xây dựng đầu thế kỷ 20 bên bờ sông An Cựu, mang kiến trúc cung đình kết hợp phong cách châu Âu. Sau này cung gắn với cuộc đời Nam Phương hoàng hậu – vị hoàng hậu cuối cùng của Việt Nam.",
    splash_image_url:
      "https://images.unsplash.com/photo-1696147861445-9fdebe294c6b?auto=format&fit=crop&w=1600&h=900&q=80",
    card_image_url:
      "https://images.unsplash.com/photo-1696147861445-9fdebe294c6b?auto=format&fit=crop&w=800&h=600&q=80",
    language1: { code: "vi", name: "Vietnamese" },
    language2: { code: "en", name: "English" },
    href: "/content/cung-an-dinh",
  },
  {
    id: 22,
    slug: "ngu-hanh-son",
    title: "Ngũ Hành Sơn",
    region: "Đà Nẵng",
    publish_date: "2026-10-26",
    description:
      "Ngũ Hành Sơn gồm năm ngọn núi đá cẩm thạch với hệ thống động, chùa và am miếu. Hằng năm, lễ hội Quán Thế Âm diễn ra tại chùa Quán Thế Âm vào ngày 19 tháng 2 âm lịch, thu hút đông đảo Phật tử và du khách.",
    splash_image_url:
      "https://images.unsplash.com/photo-1464809142576-df63ca4ed7f0?auto=format&fit=crop&w=1600&h=900&q=80",
    card_image_url:
      "https://images.unsplash.com/photo-1464809142576-df63ca4ed7f0?auto=format&fit=crop&w=800&h=600&q=80",
    language1: { code: "vi", name: "Vietnamese" },
    language2: { code: "en", name: "English" },
    href: "/content/ngu-hanh-son",
  },
];

function getCardImageUrl(item?: TriptychCardData): string {
  if (!item) return LOCAL_FALLBACK_IMAGE;
  return item.splash_image_url || item.card_image_url || LOCAL_FALLBACK_IMAGE;
}

function selectFeaturedTriptychItems(
  sourceItems?: TriptychCardData[]
): TriptychCardData[] {
  if (!sourceItems || sourceItems.length === 0) {
    return DEFAULT_HERO_ITEMS;
  }

  // Ưu tiên chọn đúng 3 di sản: Lăng Tự Đức, Cung An Định, Ngũ Hành Sơn
  const picked: TriptychCardData[] = [];
  for (let i = 0; i < FEATURED_HERO_SLUGS.length; i++) {
    const slugCandidates = FEATURED_HERO_SLUGS[i];
    const fallback = DEFAULT_HERO_ITEMS[i];
    const matched = sourceItems.find((item) =>
      (slugCandidates as readonly string[]).includes(item.slug)
    );
    if (matched) {
      picked.push({
        ...matched,
        card_image_url:
          matched.card_image_url ||
          matched.splash_image_url ||
          fallback.card_image_url,
        splash_image_url:
          matched.splash_image_url ||
          matched.card_image_url ||
          fallback.splash_image_url,
        href: matched.href || `/content/${matched.slug}`,
      });
    } else if (sourceItems.length === 3 && sourceItems[i]) {
      const item = sourceItems[i];
      picked.push({
        ...item,
        card_image_url:
          item.card_image_url || item.splash_image_url || fallback.card_image_url,
        splash_image_url:
          item.splash_image_url ||
          item.card_image_url ||
          fallback.splash_image_url,
        href: item.href || `/content/${item.slug}`,
      });
    } else {
      picked.push(fallback);
    }
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
  const [fetchedItems, setFetchedItems] = useState<TriptychCardData[] | null>(
    null
  );

  useEffect(() => {
    if (items && items.length > 0) return;
    let active = true;
    fetchHeritages()
      .then((data) => {
        if (active && Array.isArray(data) && data.length > 0) {
          setFetchedItems(data);
        }
      })
      .catch(() => {
        // Fallback sang DEFAULT_HERO_ITEMS khi API chưa bật
      });
    return () => {
      active = false;
    };
  }, [items]);

  const displayItems = useMemo(() => {
    const source = items && items.length > 0 ? items : fetchedItems ?? undefined;
    return selectFeaturedTriptychItems(source);
  }, [items, fetchedItems]);

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

        {/* Cột bên phải: Triptych Section (.hp_triptych) */}
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
      </div>
    </section>
  );
}

export const HomeSection = HeroSection;
export default HeroSection;
