"use client";

import { useEffect, useState } from "react";
import { HeroSection, DiscoverMoreSection, HeritageCarouselSection } from "@/features/home";
import { ArtifactCollectionSection } from "@/features/home/ArtifactCollectionSection";
import { CatalogInfoModal } from "@/features/home/CatalogInfoModal";
import { appendCatalogPage, toCatalogCard } from "@/features/home/catalog-cards";
import { getCatalogSection, getCatalogSections, type CatalogContent, type CatalogSections, type SectionKey } from "@/services/catalog.service";
import styles from "@/features/home/HeritageCarouselSection.module.css";

const SECTIONS: { key: SectionKey; title: string; description: string; empty: string }[] = [
  { key: "featured", title: "Featured Experiences", description: "Những trải nghiệm được tuyển chọn để bắt đầu hành trình khám phá.", empty: "Chưa có trải nghiệm nổi bật được tuyển chọn." },
  { key: "artifacts_treasures", title: "Artifacts & Treasures", description: "Những bộ sưu tập có nguồn tư liệu và câu chuyện riêng.", empty: "Chưa có bộ sưu tập hiện vật đã được xuất bản." },
  { key: "artifact_collection", title: "Heritage Artifacts Collection", description: "", empty: "" },
  { key: "people_traditions", title: "People & Traditions", description: "Nhân vật, nghệ nhân và truyền thống văn hóa được ghi nhận.", empty: "Chưa có nội dung nhân vật hoặc truyền thống được xuất bản." },
  { key: "festivals_practices", title: "Festivals & Community Practices", description: "Khám phá các lễ hội, nghi lễ và thực hành văn hóa qua câu chuyện của chính chúng.", empty: "Chưa có lễ hội hoặc thực hành văn hóa được xuất bản." },
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
      if (!controller.signal.aborted) setError("Chưa tải được nội dung. Bạn có thể thử lại khi máy chủ sẵn sàng.");
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
    } catch { setError("Chưa tải được trang tiếp theo. Vui lòng thử lại."); }
    finally { setLoadingMore(null); }
  };

  return <div className={styles.homePage}>
    <HeroSection items={sections?.featured.items.map(toCatalogCard) ?? []} loading={loading} onInfo={info} />
    {SECTIONS.map(({ key, title, description, empty }) => <div key={key}>
      {key === "artifact_collection"
        ? <ArtifactCollectionSection items={sections?.[key].items ?? []} loading={loading} error={error} onRetry={retry} onInfo={info} />
        : <HeritageCarouselSection title={title} description={description}
          items={sections?.[key].items.map(toCatalogCard) ?? []} loading={loading} error={error}
          onRetry={retry} onCardClick={info} emptyMessage={empty} useFirstCardBackdrop
          className={key === "festivals_practices" ? styles.festivalSection : undefined} />}
      {sections?.[key].next_offset != null && <div className={styles.loadMore}>
        <button onClick={() => more(key)} disabled={loadingMore !== null}
          aria-label={`Xem thêm ${title}`}>{loadingMore === key ? "Đang tải…" : "Xem thêm"}</button>
      </div>}
    </div>)}
    <DiscoverMoreSection />
    <CatalogInfoModal item={selected} onClose={() => setSelected(null)} />
  </div>;
}
