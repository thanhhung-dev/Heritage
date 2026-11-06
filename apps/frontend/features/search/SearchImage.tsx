"use client";

import Image from "next/image";
import { PictureOutlined } from "@ant-design/icons";
import { useState } from "react";
import { searchImageUrl } from "@/features/search/catalogue";
import styles from "@/features/search/search.module.css";

function ResolvedImage({ sources, sizes, priority }: { sources: string[]; sizes: string; priority: boolean }) {
  const [index, setIndex] = useState(0);
  const src = sources[index];
  return !src ? <PictureOutlined className={styles.imagePlaceholder} aria-hidden />
    : <Image key={src} src={src} alt="" fill unoptimized sizes={sizes} priority={priority}
      onError={() => setIndex((current) => sources[current] === src ? current + 1 : current)} />;
}

export function SearchImage({ src, fallbacks = [], sizes, priority = false }: {
  src?: string | null; fallbacks?: (string | null | undefined)[]; sizes: string; priority?: boolean;
}) {
  const sources = [...new Set([src, ...fallbacks].map(searchImageUrl).filter((url): url is string => Boolean(url)))];
  return sources.length ? <ResolvedImage key={JSON.stringify(sources)} sources={sources} sizes={sizes} priority={priority} />
    : <PictureOutlined className={styles.imagePlaceholder} aria-hidden />;
}
