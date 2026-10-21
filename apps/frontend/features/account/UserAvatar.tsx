"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import styles from "./user-avatar.module.css";

interface UserAvatarProps {
  /** Remote avatar URL (Google profile photo, profile API, …). */
  src?: string | null;
  /** Used for the accessible label and the fallback initial. */
  name?: string | null;
  size?: number;
  className?: string;
  alt?: string;
}

function getInitial(name?: string | null): string {
  const trimmed = name?.trim();
  return trimmed ? trimmed.charAt(0).toUpperCase() : "H";
}

/**
 * Shared circular avatar with an orange initial fallback.
 *
 * Uses next/image (remote hosts are allow-listed in next.config.js) and the
 * image `onError` callback to fall back gracefully when a Google avatar URL
 * is broken or expires.
 */
export function UserAvatar({
  src,
  name,
  size = 40,
  className,
  alt = "",
}: UserAvatarProps) {
  const [failed, setFailed] = useState(false);

  // A new URL should get a fresh chance to load.
  useEffect(() => {
    setFailed(false);
  }, [src]);

  const classes = [styles.avatar, className].filter(Boolean).join(" ");
  const showImage = Boolean(src) && !failed;

  return (
    <span
      className={classes}
      style={{
        width: size,
        height: size,
        fontSize: Math.max(12, Math.round(size * 0.38)),
      }}
      aria-hidden={alt ? undefined : true}
    >
      {showImage ? (
        <Image
          src={src as string}
          alt={alt}
          width={size}
          height={size}
          className={styles.image}
          onError={() => setFailed(true)}
          unoptimized
        />
      ) : (
        <span className={styles.fallback}>{getInitial(name)}</span>
      )}
    </span>
  );
}
