"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { ApiError } from "@/config/api";
import { getCatalogDetail, type CatalogDetail as Detail } from "@/services/catalog.service";
import { ArtifactFacts } from "./ArtifactFacts";
import styles from "./catalog-detail.module.css";

const KIND_LABELS = { place: "Địa điểm di sản", artifact: "Cổ vật & hiện vật", collection: "Bộ sưu tập",
  event: "Lễ hội & sự kiện", person: "Nhân vật & nghệ nhân", practice: "Thực hành văn hóa" };

export function CatalogDetail({ slug }: { slug: string }) {
  const [item, setItem] = useState<Detail | null>(null);
  const [error, setError] = useState<string>();
  const [attempt, setAttempt] = useState(0);
  const [imageFailed, setImageFailed] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setItem(null); setError(undefined); setImageFailed(false);
    getCatalogDetail(slug, controller.signal).then((data) => { if (!controller.signal.aborted) setItem(data); })
      .catch((failure: unknown) => {
        if (!controller.signal.aborted) setError(failure instanceof ApiError && failure.status === 404
          ? "Nội dung chưa được xuất bản hoặc không còn tồn tại."
          : "Chưa kết nối được với kho tư liệu. Vui lòng thử lại.");
      });
    return () => controller.abort();
  }, [slug, attempt]);
  return <main className={styles.page}>
    <Link href="/" className={styles.back}>← Khám phá di sản</Link>
    {error ? <div role="alert" className={styles.state}><h1>Chưa thể mở nội dung</h1><p>{error}</p>
      <button onClick={() => setAttempt((value) => value + 1)}>Thử lại</button></div>
      : !item ? <p className={styles.state} role="status">Đang mở kho tư liệu…</p>
      : <article>
        <header className={styles.heading}><p className={styles.eyebrow}>{KIND_LABELS[item.entity_type]}</p>
          <h1>{item.title}</h1>{item.region && <p>{item.region}</p>}</header>
        <div className={styles.layout}>
          <div>{item.card_image_url && !imageFailed && <Image src={item.card_image_url} alt={item.title}
            width={1200} height={900} priority unoptimized className={styles.image} onError={() => setImageFailed(true)} />}
            {item.description && <div className={styles.description}>{item.description}</div>}
          </div>
          <aside className={styles.facts}><h2>Thông tin tư liệu</h2><ArtifactFacts item={item} />
            {item.source_url ? <a href={item.source_url} target="_blank" rel="noopener noreferrer">Xem nguồn tư liệu ↗</a>
              : <p>Thông tin được kế thừa từ bản ghi di sản đã xuất bản.</p>}
            {item.entity_type === "place" && item.heritage_slug && <Link href={item.href}>Bắt đầu tham quan 3D →</Link>}
          </aside>
        </div>
        {!!item.related_entities.length && <section className={styles.related}><h2>Nội dung liên quan</h2>
          <div>{item.related_entities.map(({ content }) => <Link href={content.href} key={content.id}>
            <span>{KIND_LABELS[content.entity_type]}</span><h3>{content.title}</h3></Link>)}</div>
        </section>}
      </article>}
  </main>;
}
