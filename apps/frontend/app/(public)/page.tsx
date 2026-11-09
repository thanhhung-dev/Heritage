"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  HeroSection,
  DiscoverMoreSection,
  HeritageCarouselSection,
  HeritageInfoModal,
  FALLBACK_HERITAGE_ITEMS,
  getCardImageUrl,
  selectFeaturedTriptychItems,
  type HeritageItem,
} from "@/features/home";
import type { TriptychCardData } from "@/components/TriptychCard/TriptychCard";
import { getHeritages } from "@/services/heritage.service";

function preloadImage(url: string): Promise<void> {
  if (!url || typeof window === "undefined") return Promise.resolve();
  return new Promise((resolve) => {
    const img = new window.Image();
    img.onload = () => resolve();
    img.onerror = () => resolve();
    img.src = url;
  });
}

export default function HomePage() {
  const router = useRouter();

  const [apiItems, setApiItems] = useState<TriptychCardData[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalItem, setModalItem] = useState<any>(null);

  useEffect(() => {
    let active = true;
    getHeritages()
      .then(async (data: any) => {
        if (!active) return;
        const list = Array.isArray(data) && data.length > 0 ? data : FALLBACK_HERITAGE_ITEMS;
        const heroItems = selectFeaturedTriptychItems(list);
        const urlsToPreload = new Set<string>();

        for (const item of heroItems) {
          const bgUrl = getCardImageUrl(item);
          const cardUrl = item.card_image_url || item.splash_image_url || bgUrl;
          if (bgUrl) urlsToPreload.add(bgUrl);
          if (cardUrl) urlsToPreload.add(cardUrl);
        }

        await Promise.all(Array.from(urlsToPreload, preloadImage));
        if (active) {
          setApiItems(list);
        }
      })
      .catch((err) => {
        console.warn("Lỗi load API heritages, dùng fallback:", err);
        if (active) {
          setApiItems(FALLBACK_HERITAGE_ITEMS);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const sourceList = (loading
    ? []
    : apiItems.length > 0
      ? apiItems
      : FALLBACK_HERITAGE_ITEMS) as unknown as HeritageItem[];

  const featuredItems = sourceList.slice(0, 5);
  const artifactItems = sourceList;
  const traditionItems = sourceList;
  const festivalItems = sourceList;

  const handleOpenInfoModal = (target: any) => {
    if (!target) return;

    if (typeof target === "string" || typeof target === "number") {
      const found = sourceList.find(
        (i: any) => String(i.slug) === String(target) || String(i.id) === String(target)
      );
      if (found) {
        setModalItem(found);
        return;
      }
      setModalItem({ slug: target, title: String(target), description: "" });
      return;
    }

    if (typeof target === "object") {
      const fullItem = sourceList.find(
        (i: any) =>
          (target.slug && i.slug === target.slug) ||
          (target.id && String(i.id) === String(target.id))
      );
      setModalItem(fullItem || target);
      return;
    }
  };

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        minHeight: "100vh",
        overflowX: "hidden",
        backgroundColor: "#07090e",
      }}
    >
      <HeroSection
        items={apiItems.length > 0 ? apiItems : (loading ? undefined : (FALLBACK_HERITAGE_ITEMS as any))}
        loading={loading}
        onInfo={handleOpenInfoModal}
      />

      <HeritageCarouselSection
        title="Featured Experiences"
        description="Curated virtual journeys and immersive stories"
        items={featuredItems}
        loading={loading}
        onCardClick={handleOpenInfoModal}
      />

      <HeritageCarouselSection
        title="Artifacts & Treasures"
        description="The tools, art, and objects that shape human history"
        items={artifactItems}
        loading={loading}
        onCardClick={handleOpenInfoModal}
      />

      <HeritageCarouselSection
        title="People & Traditions"
        description="Community members share personal stories and memories"
        items={traditionItems}
        loading={loading}
        onCardClick={handleOpenInfoModal}
      />

      <HeritageCarouselSection
        title="Festivals & Community Practices"
        description="The rituals and customs that bring heritage to life"
        items={festivalItems}
        loading={loading}
        onCardClick={handleOpenInfoModal}
      />

      <DiscoverMoreSection />

      <HeritageInfoModal
        item={modalItem}
        onClose={() => setModalItem(null)}
      />
    </div>
  );
}
