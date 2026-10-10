"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { useHeritageTour } from "@/context/heritage-tour";
import styles from "./content-shell.module.css";

/**
 * `/content/{slug}` — landing screen.
 *
 * Renders IMMEDIATELY from the payload (demo data is the fallback until the
 * real backend payload arrives). The 3D scene loading (your team's part)
 * hooks into `useHeritageTour()`. When loading completes the user presses
 * Start → navigates to `/content/{slug}/s0`.
 */
export default function ContentLoadingPage() {
  const { slug } = useParams<{ slug: string }>();
  const { payload, status, error } = useHeritageTour();

  return (
    <div className={styles.loading}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        className={styles.splash}
        src={payload.heritage.splash_image_url ?? undefined}
        alt=""
      />
      <h1 className={styles.title}>{payload.heritage.title ?? slug}</h1>
      {payload.heritage.tagline ? (
        <p className={styles.subtitle}>{payload.heritage.tagline}</p>
      ) : null}
      <p className={styles.mode}>
        {status === "demo"
          ? "Chế độ demo — dữ liệu mẫu"
          : error
            ? "Đang dùng dữ liệu đã tải"
            : null}
      </p>
      {error ? <p className={styles.errorMessage}>{error}</p> : null}
      <Link className={styles.startButton} href={`/content/${slug}/s0`}>
        Bắt đầu trải nghiệm
      </Link>
    </div>
  );
}