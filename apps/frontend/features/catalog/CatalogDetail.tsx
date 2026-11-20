"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { ApiError } from "@/config/api";
import { getCatalogDetail, type CatalogDetail as Detail } from "@/services/catalog.service";
import { ArtifactFacts } from "./ArtifactFacts";
import styles from "./catalog-detail.module.css";

const KIND_LABELS = { place: "Heritage place", artifact: "Artifacts & treasures", collection: "Collection",
  event: "Festivals & events", person: "People & artisans", practice: "Cultural practice" };

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
          ? "This content has not been published or is no longer available."
          : "Unable to connect to the collection. Please try again.");
      });
    return () => controller.abort();
  }, [slug, attempt]);
  return <main className={styles.page}>
    <Link href="/" className={styles.back}>← Discover heritage</Link>
    {error ? <div role="alert" className={styles.state}><h1>Unable to open this story</h1><p>{error}</p>
      <button onClick={() => setAttempt((value) => value + 1)}>Try again</button></div>
      : !item ? <p className={styles.state} role="status">Opening the collection…</p>
      : <article>
        <header className={styles.heading}><p className={styles.eyebrow}>{KIND_LABELS[item.entity_type]}</p>
          <h1>{item.title}</h1>{item.region && <p>{item.region}</p>}</header>
        <div className={styles.layout}>
          <div>{item.card_image_url && !imageFailed && <Image src={item.card_image_url} alt={item.title}
            width={1200} height={900} priority unoptimized className={styles.image} onError={() => setImageFailed(true)} />}
            {item.description && <div className={styles.description}>{item.description}</div>}
          </div>
          <aside className={styles.facts}><h2>Collection information</h2><ArtifactFacts item={item} />
            {item.source_url ? <a href={item.source_url} target="_blank" rel="noopener noreferrer">View source reference ↗</a>
              : <p>Information comes from the published heritage record.</p>}
            {item.entity_type === "place" && item.heritage_slug && <Link href={item.href}>Start the 3D experience →</Link>}
          </aside>
        </div>
        {!!item.related_entities.length && <section className={styles.related}><h2>Related stories</h2>
          <div>{item.related_entities.map(({ content }) => <Link href={content.href} key={content.id}>
            <span>{KIND_LABELS[content.entity_type]}</span><h3>{content.title}</h3></Link>)}</div>
        </section>}
      </article>}
  </main>;
}
