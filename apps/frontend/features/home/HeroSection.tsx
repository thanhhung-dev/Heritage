"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import TriptychCard, {
  type TriptychCardData,
} from "@/components/TriptychCard/TriptychCard";
import mockData from "@/mocks/heritage-mock.json";
import styles from "./HeroSection.module.css";
import { HeritageDetailModal, type HeritageItem } from "./HeritageDetailModal";

export interface HeroTileProps {
  eyebrow?: string;
  title?: React.ReactNode;
  description?: string;
  subDescription?: string;
  className?: string;
}

/**
 * Component bên trái: HeroTile
 * - text-align: left; align-items: flex-start;
 * - Tiêu đề ngắt dòng chuẩn Figma: Every Place Has a <br /> Story
 * - 2 đoạn mô tả 14px, color: rgba(255, 255, 255, 0.7), không text shadow
 */
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
    <div className={[styles.heroTile, className].filter(Boolean).join(" ")}>
      {eyebrow ? <p className={styles.heroTileEyebrow}>{eyebrow}</p> : null}
      <h1 className={styles.heroTitle}>{renderedTitle}</h1>
      {description ? (
        <p className={styles.heroDescription}>{description}</p>
      ) : null}
      {subDescription ? (
        <p className={styles.heroSubDescription}>{subDescription}</p>
      ) : null}
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
 * Lấy 3 di sản chuẩn khớp mẫu thiết kế Figma (An Định, Tự Đức, Ngũ Hành Sơn)
 */
function getDefaultHeroItems(): TriptychCardData[] {
  const typedMocks = mockData as unknown as TriptychCardData[];
  const targetSlugs = ["an-dinh-palace", "tu-duc-tomb", "marble-mountains"];
  const matched = targetSlugs
    .map((slug) => typedMocks.find((item) => item.slug === slug))
    .filter((item): item is TriptychCardData => Boolean(item));

  const items =
    matched.length >= 3 ? matched.slice(0, 3) : typedMocks.slice(0, 3);

  // Đảm bảo card Cung An Định luôn có ảnh local thực tế tuyệt đẹp và ổn định
  return items.map((item) => {
    if (item.slug === "an-dinh-palace") {
      return {
        ...item,
        card_image_url: LOCAL_FALLBACK_IMAGE,
        splash_image_url: LOCAL_FALLBACK_IMAGE,
      };
    }
    return item;
  });
}

function getCardImageUrl(item?: TriptychCardData): string {
  if (!item) return LOCAL_FALLBACK_IMAGE;
  if (item.slug === "an-dinh-palace") {
    return LOCAL_FALLBACK_IMAGE;
  }
  return item.splash_image_url || item.card_image_url || LOCAL_FALLBACK_IMAGE;
}

/**
 * Component khung chính: HeroSection (HomeSection)
 * 1. heroBlurredBg: Lớp nền mờ đằng sau (Blurred Heritage Background) theo currentBg
 * 2. heroOverlayGradient: Lớp gradient phủ tối để làm nổi bật chữ
 * 3. heroLayout: Container max-width 1680px, padding 0 40px, align-items: flex-start
 * 4. 3 TriptychCard: Chiều cao cố định 780px, border-radius 24px, active flex: 2.5
 */
export function HeroSection({
  items,
  title,
  description,
  subDescription,
  eyebrow,
  onInfo,
  exploreLabel = "Khám phá",
  infoLabel = "Chi tiết",
  className,
}: HeroSectionProps) {
  const router = useRouter();

  const displayItems = useMemo(() => {
    if (items && items.length > 0) {
      return items.slice(0, 3);
    }
    return getDefaultHeroItems();
  }, [items]);

  const defaultBg = getCardImageUrl(displayItems[0]);

  // State lưu trữ đường dẫn ảnh của card đang active/hover (mặc định lấy ảnh card 1)
  const [currentBg, setCurrentBg] = useState<string>(defaultBg);

  // State quản lý Modal Info
  const [selectedHeritage, setSelectedHeritage] = useState<HeritageItem | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleCardHover = (item: TriptychCardData) => {
    const url = getCardImageUrl(item);
    if (url && url !== currentBg) {
      setCurrentBg(url);
    }
  };

  // Hàm mở Modal Info khi bấm nút Chi tiết hoặc click card
  const handleOpenInfoModal = (item: TriptychCardData) => {
    if (onInfo) {
      onInfo(item.slug);
    }

    const anyItem = item as any;
    setSelectedHeritage({
      id: item.slug,
      title: anyItem.title || anyItem.name || "Di sản văn hóa",
      category: anyItem.category || anyItem.type || "Di tích lịch sử",
      period: anyItem.period || anyItem.era || "Việt Nam",
      description:
        anyItem.description ||
        anyItem.short_description ||
        "Khám phá câu chuyện lịch sử và vẻ đẹp kiến trúc đặc sắc của di sản này.",
      imageUrl: getCardImageUrl(item),
    });
    setIsModalOpen(true);
  };

  // Điều hướng sang trang chi tiết khi bấm nút trong Modal
  const handleNavigateDetail = (slug: string) => {
    setIsModalOpen(false);
    router.push(`/preview?id=${slug}`);
  };

  return (
    <section
      className={[styles.heroSection, className].filter(Boolean).join(" ")}
      aria-label="Heritage Hero"
    >
      {/* 1. Lớp ảnh nền mờ đằng sau (Blurred Heritage Background) */}
      <div
        className={styles.heroBlurredBg}
        style={{
          backgroundImage: `url(${currentBg || LOCAL_FALLBACK_IMAGE})`,
        }}
        aria-hidden="true"
      />

      {/* 2. Lớp gradient phủ tối để làm nổi bật chữ */}
      <div className={styles.heroOverlayGradient} aria-hidden="true" />

      {/* Container nội dung */}
      <div className={styles.heroLayout}>
        {/* Cột bên trái: HeroTile */}
        <HeroTile
          eyebrow={eyebrow}
          title={title}
          description={description}
          subDescription={subDescription}
        />

        {/* Cột bên phải: 3 Triptych Cards */}
        <div className={styles.triptychList}>
          {displayItems.map((item) => (
            <div
              key={`hero-${item.slug}`}
              className={styles.triptychCard}
              onMouseEnter={() => handleCardHover(item)}
              onFocus={() => handleCardHover(item)}
            >
              <TriptychCard
                item={item}
                exploreLabel={exploreLabel}
                infoLabel={infoLabel}
                onInfo={() => handleOpenInfoModal(item)}
              />
            </div>
          ))}
        </div>
      </div>

      {/* 3. Modal hiển thị thông tin di sản */}
      <HeritageDetailModal
        isOpen={isModalOpen}
        item={selectedHeritage}
        onClose={() => setIsModalOpen(false)}
        onNavigate={handleNavigateDetail}
      />
    </section>
  );
}

export const HomeSection = HeroSection;
export default HeroSection;