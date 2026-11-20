"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import type { CatalogContent } from "@/services/catalog.service";
import { ArtifactFacts } from "@/features/catalog/ArtifactFacts";
import styles from "./ArtifactCollectionSection.module.css";

function ArtifactImage({ item }: { item: CatalogContent }) {
  const [failed, setFailed] = useState(false);
  return <div className={styles.image}>
    {item.card_image_url && !failed && <Image src={item.card_image_url} alt={item.title} fill
      unoptimized loading="lazy" sizes="(max-width: 640px) 100vw, (max-width: 1100px) 50vw, 25vw"
      onError={() => setFailed(true)} />}
    {(!item.card_image_url || failed) && <span className={styles.imageMissing}>Chưa có hình ảnh</span>}
  </div>;
}

export function ArtifactCollectionSection({ items, loading, error, onRetry, onInfo }: {
  items: CatalogContent[]; loading: boolean; error?: string; onRetry: () => void; onInfo: (slug: string) => void;
}) {
  return <section className={styles.section} aria-labelledby="artifact-collection-title" aria-busy={loading}>
    <header className={styles.header}>
      <p className={styles.eyebrow}>Heritage Artifacts Collection</p>
      <h2 id="artifact-collection-title">Kho tàng Cổ vật &amp; Hiện vật</h2>
      <p>Khám phá những hiện vật và câu chuyện được lưu giữ, cùng thông tin có nguồn xác minh.</p>
    </header>
    {error && <div className={styles.state} role="status">{error} <button onClick={onRetry}>Thử lại</button></div>}
    {loading && !items.length ? <div className={styles.grid} aria-label="Đang tải bộ sưu tập">
      {[0, 1, 2, 3].map((slot) => <div className={styles.skeleton} key={slot} aria-hidden="true" />)}
    </div> : !items.length ? <p className={styles.state} role="status">
      Chưa có cổ vật hoặc hiện vật đã được xác minh và xuất bản. Bộ sưu tập sẽ được cập nhật khi có nội dung mới.
    </p> : <div className={styles.grid}>{items.map((item) => <article className={styles.card} key={item.id}>
      <Link href={item.href} aria-label={`Khám phá ${item.title}`}><ArtifactImage item={item} /></Link>
      <div className={styles.cardBody}>
        <h3><Link href={item.href}>{item.title}</Link></h3>
        {item.description && <p className={styles.description}>{item.description}</p>}
        <ArtifactFacts item={item} />
        <div className={styles.actions}><Link href={item.href}>Khám phá hiện vật <span aria-hidden="true">↗</span></Link>
          <button onClick={() => onInfo(item.slug)}>Thông tin</button></div>
      </div>
    </article>)}</div>}
  </section>;
}
