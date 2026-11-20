"use client";

import { useEffect, useState } from "react";
import { HeroSection, DiscoverMoreSection, HeritageCarouselSection } from "@/features/home";
import { CatalogInfoModal } from "@/features/home/CatalogInfoModal";
import { appendCatalogPage, toCatalogCard } from "@/features/home/catalog-cards";
import { getCatalogSection, getCatalogSections, type CatalogContent, type CatalogSections, type SectionKey } from "@/services/catalog.service";
import styles from "@/features/home/HeritageCarouselSection.module.css";

const SECTIONS: { key: SectionKey; title: string; description: string; empty: string }[] = [
  { key: "featured", title: "Featured Experiences", description: "Curated experiences to begin your journey of discovery.", empty: "No featured experiences have been selected yet." },
  { key: "artifacts_treasures", title: "Artifacts & Treasures", description: "Discover collections with their own stories and documented sources.", empty: "No artifact collections have been published yet." },
  { key: "artifact_collection", title: "Heritage Artifacts Collection", description: "Explore artifacts and the stories they preserve, supported by verified sources.", empty: "No verified artifacts have been published yet." },
  { key: "people_traditions", title: "People & Traditions", description: "Meet the people, artisans, and traditions that shape cultural heritage.", empty: "No stories about people or traditions have been published yet." },
  { key: "festivals_practices", title: "Festivals & Community Practices", description: "Explore festivals, rituals, and cultural practices through their own stories.", empty: "No festivals or cultural practices have been published yet." },
];

export default function HomePage() {
  const [sections, setSections] = useState<CatalogSections | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [attempt, setAttempt] = useState(0);
  const [loadingMore, setLoadingMore] = useState<SectionKey | null>(null);
  const [selected, setSelected] = useState<CatalogContent | null>(null);
  const retry = () => setAttempt((value) => value + 1);

  useEffect(() => {
    const controller = new AbortController();
    getCatalogSections(controller.signal).then((data) => {
      if (controller.signal.aborted) return;
      setSections(data);
      setError(undefined);
      setSelected((previous) => previous
        ? Object.values(data).flatMap((page) => page.items).find((item) => item.id === previous.id) ?? null : null);
    }).catch(() => {
      if (!controller.signal.aborted) setError("Content is unavailable right now. Please try again when the server is ready.");
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [attempt]);

  useEffect(() => {
    const refresh = () => { if (document.visibilityState === "visible") retry(); };
    const timer = window.setInterval(refresh, 30_000);
    window.addEventListener("focus", refresh);
    window.addEventListener("online", refresh);
    return () => { window.clearInterval(timer); window.removeEventListener("focus", refresh); window.removeEventListener("online", refresh); };
  }, []);

  const info = (slug: string) => setSelected(sections
    ? Object.values(sections).flatMap((page) => page.items).find((item) => item.slug === slug) ?? null : null);
  const more = async (key: SectionKey) => {
    const offset = sections?.[key].next_offset;
    if (offset == null || loadingMore) return;
    setLoadingMore(key);
    try {
      const next = await getCatalogSection(key, offset);
      setSections((current) => current && current[key].next_offset === offset
        ? { ...current, [key]: appendCatalogPage(current[key], next) } : current);
    } catch { setError("Unable to load more content. Please try again."); }
    finally { setLoadingMore(null); }
  };

  return <div className={styles.homePage}>
    <HeroSection items={sections?.featured.items.map(toCatalogCard) ?? []} loading={loading} onInfo={info} />
    {SECTIONS.map(({ key, title, description, empty }) => <div key={key}>
      <HeritageCarouselSection title={title} description={description}
          items={sections?.[key].items.map(toCatalogCard) ?? []} loading={loading} error={error}
          onRetry={retry} onCardClick={info} emptyMessage={empty} useFirstCardBackdrop
          className={key === "festivals_practices" ? styles.festivalSection : undefined} />
      {sections?.[key].next_offset != null && <div className={styles.loadMore}>
        <button onClick={() => more(key)} disabled={loadingMore !== null}
          aria-label={`Load more ${title}`}>{loadingMore === key ? "Loading…" : "Load more"}</button>
      </div>}
    </div>)}
    <DiscoverMoreSection />
    <CatalogInfoModal item={selected} onClose={() => setSelected(null)} />
  </div>;
}
