"use client";

import Image from "next/image";
import { PictureOutlined } from "@ant-design/icons";
import { useState } from "react";
import { searchImageUrl } from "@/features/search/catalogue";
import styles from "@/features/search/search.module.css";

function ResolvedImage({ src, sizes, priority }: { src: string; sizes: string; priority: boolean }) {
  const [failed, setFailed] = useState(false);
  return failed ? <PictureOutlined className={styles.imagePlaceholder} aria-hidden />
    : <Image src={src} alt="" fill unoptimized sizes={sizes} priority={priority} onError={() => setFailed(true)} />;
}

export function SearchImage({ src, sizes, priority = false }: { src?: string | null; sizes: string; priority?: boolean }) {
  const url = searchImageUrl(src);
  return url ? <ResolvedImage key={url} src={url} sizes={sizes} priority={priority} />
    : <PictureOutlined className={styles.imagePlaceholder} aria-hidden />;
}
