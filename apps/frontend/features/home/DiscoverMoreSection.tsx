"use client";

import Link from "next/link";
import styles from "./DiscoverMoreSection.module.css";

export interface DiscoverMoreSectionProps {
  title?: string;
  subtitle?: string;
  primaryLabel?: string;
  primaryHref?: string;
  secondaryLabel?: string;
  secondaryHref?: string;
  className?: string;
}

/**
 * Section CTA "Discover More"
 * - Nền đen #0B0C0E với quầng sáng cam chuẩn Figma: radial-gradient(45% 55% at 50% 60%, rgba(195, 90, 30, 0.16) 0%, rgba(11, 12, 14, 0) 100%)
 * - Subtitle 1 dòng: "Explore our complete collection of immersive heritage experiences"
 * - Căn container 1280px thụt lề 80px 2 bên
 * - Nút "Browse Library" (#FF6422) & "Explore Map" (kính tối mờ rgba(255, 255, 255, 0.08))
 */
export function DiscoverMoreSection({
  title = "Discover More",
  subtitle = "Explore our complete collection of immersive heritage experiences",
  primaryLabel = "Browse Library",
  primaryHref = "/library",
  secondaryLabel = "Explore Map",
  secondaryHref = "/map",
  className,
}: DiscoverMoreSectionProps) {
  return (
    <section
      className={[styles.discoverSection, className].filter(Boolean).join(" ")}
      aria-label="Discover More CTA"
    >
      <div className={styles.content}>
        <h2 className={styles.title}>{title}</h2>
        <p className={styles.subtitle}>{subtitle}</p>

        <div className={styles.buttonGroup}>
          <Link href={primaryHref} className={styles.btnPrimary}>
            {primaryLabel}
          </Link>
          <Link href={secondaryHref} className={styles.btnSecondary}>
            {secondaryLabel}
          </Link>
        </div>
      </div>
    </section>
  );
}

export default DiscoverMoreSection;
