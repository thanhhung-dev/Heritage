"use client";

import Link from "next/link";
import styles from "./DiscoverMoreSection.module.css";
import mockData from "@/mocks/heritage-mock.json";

export interface RecommendedItem {
  slug: string;
  title: string;
  category?: string;
  location?: string;
  card_image_url?: string;
  splash_image_url?: string;
}

export interface DiscoverMoreSectionProps {
  title?: string;
  subtitle?: string;
  primaryLabel?: string;
  primaryHref?: string;
  secondaryLabel?: string;
  secondaryHref?: string;
  items?: RecommendedItem[];
  className?: string;
}

const DEFAULT_IMAGE = "/images/cung-an-dinh.jpg";

export function DiscoverMoreSection({
  title = "Discover More",
  subtitle = "Explore our complete collection of immersive heritage experiences",
  primaryLabel = "Browse Library",
  primaryHref = "/library",
  secondaryLabel = "Explore Map",
  secondaryHref = "/map",
  items,
  className,
}: DiscoverMoreSectionProps) {
  // Lấy danh sách cold-start recommendation từ mock data nếu không truyền props
  const recommendations: RecommendedItem[] =
    items && items.length > 0
      ? items
      : (mockData as unknown as RecommendedItem[]).slice(0, 4);

  return (
    <section
      className={[styles.discoverSection, className].filter(Boolean).join(" ")}
      aria-label="Discover More Heritage"
    >
      <div className={styles.container}>
        <div className={styles.header}>
          <h2 className={styles.title}>{title}</h2>
          <p className={styles.subtitle}>{subtitle}</p>
        </div>

        {/* Cold-start recommendation shelf */}
        <div className={styles.shelfGrid}>
          {recommendations.map((item) => {
            const bgImage =
              item.card_image_url || item.splash_image_url || DEFAULT_IMAGE;
            return (
              <Link
                key={item.slug}
                href={`/preview?id=${item.slug}`}
                className={styles.shelfCard}
              >
                <div
                  className={styles.cardMedia}
                  style={{ backgroundImage: `url(${bgImage})` }}
                >
                  <span className={styles.cardBadge}>
                    {item.category || "Di sản"}
                  </span>
                </div>
                <div className={styles.cardInfo}>
                  <h3 className={styles.cardTitle}>{item.title}</h3>
                  {item.location ? (
                    <p className={styles.cardLocation}>{item.location}</p>
                  ) : null}
                </div>
              </Link>
            );
          })}
        </div>

        <div className={styles.actions}>
          <Link href={primaryHref} className={styles.primaryBtn}>
            {primaryLabel}
          </Link>
          <Link href={secondaryHref} className={styles.secondaryBtn}>
            {secondaryLabel}
          </Link>
        </div>
      </div>
    </section>
  );
}

export default DiscoverMoreSection;