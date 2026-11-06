"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import ContentLoading from "@/components/Loading/ContentLoading";
import {
  HeroSection,
  DiscoverMoreSection,
  HeritageCarouselSection,
  getCardImageUrl,
  selectFeaturedTriptychItems,
  type HeritageItem,
} from "@/features/home";
import type { TriptychCardData } from "@/components/TriptychCard/TriptychCard";
import { fetchHeritages } from "@/lib/heritage";

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

  useEffect(() => {
    let active = true;
    fetchHeritages()
      .then(async (data) => {
        if (!active) return;
        const list = Array.isArray(data) ? data : [];
        const heroItems = selectFeaturedTriptychItems(list);
        const urlsToPreload = new Set<string>();
        for (const item of heroItems) {
          const bgUrl = getCardImageUrl(item);
          const cardUrl =
            item.card_image_url || item.splash_image_url || bgUrl;
          if (bgUrl) urlsToPreload.add(bgUrl);
          if (cardUrl) urlsToPreload.add(cardUrl);
        }
        await Promise.all(Array.from(urlsToPreload, preloadImage));
        if (active) {
          setApiItems(list);
        }
      })
      .catch(() => {
        // API lỗi ⇒ để trống, các section tự ẩn. Không còn dữ liệu mock thay thế.
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  // `TriptychCardData` (hero) và `HeritageItem` (carousel) là hai shape cho cùng
  // dữ liệu API; cast một lần ở đây thay vì nới kiểu ở cả hai component.
  const sourceList = apiItems as unknown as HeritageItem[];

  const featuredItems = sourceList.slice(0, 10);
  const artifactItems = sourceList.slice(8, 18);
  const traditionItems = sourceList.slice(14, 24);
  const festivalItems = sourceList.slice(20, 30);

  const handleCardClick = (slug: string) => {
    router.push(`/content/${slug}`);
  };

  if (loading) {
    return (
      <div
        style={{
          position: "relative",
          width: "100%",
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#0b0c0e",
        }}
      >
        <ContentLoading label="Loading heritage experiences…" />
      </div>
    );
  }

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        minHeight: "100vh",
        overflowX: "hidden",
        backgroundColor: "#0b0c0e",
      }}
    >
      {/* 1. HERO SECTION (3 Featured Cards: Lăng Tự Đức, Cung An Định, Ngũ Hành Sơn) */}
      <HeroSection
        items={apiItems.length > 0 ? apiItems : undefined}
        loading={loading}
        onInfo={handleCardClick}
      />

      {/* 2. FEATURED EXPERIENCES SECTION */}
      <HeritageCarouselSection
        title="Featured Experiences"
        description="Curated virtual journeys and immersive stories"
        items={featuredItems}
        onCardClick={handleCardClick}
      />

      {/* 3. ARTIFACTS & TREASURES SECTION */}
      <HeritageCarouselSection
        title="Artifacts & Treasures"
        description="The tools, art, and objects that shape human history"
        items={artifactItems}
        onCardClick={handleCardClick}
      />

      {/* 4. PEOPLE & TRADITIONS SECTION */}
      <HeritageCarouselSection
        title="People & Traditions"
        description="Community members share personal stories and memories"
        items={traditionItems}
        onCardClick={handleCardClick}
      />

      {/* 5. FESTIVALS & COMMUNITY PRACTICES SECTION */}
      <HeritageCarouselSection
        title="Festivals & Community Practices"
        description="The rituals and customs that bring heritage to life"
        items={festivalItems}
        onCardClick={handleCardClick}
      />

      {/* 6. DISCOVER MORE CTA SECTION */}
      <DiscoverMoreSection />
    </div>
  );
}
