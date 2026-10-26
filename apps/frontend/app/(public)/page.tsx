"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  HeroSection,
  DiscoverMoreSection,
  HeritageCarouselSection,
  type HeritageItem,
} from "@/features/home";
import type { TriptychCardData } from "@/components/TriptychCard/TriptychCard";
import { fetchHeritages } from "@/lib/heritage";
import mockData from "@/mocks/heritage-mock.json";

export default function HomePage() {
  const router = useRouter();
  const fallbackMocks = mockData as unknown as HeritageItem[];

  const [apiItems, setApiItems] = useState<TriptychCardData[]>([]);

  useEffect(() => {
    let active = true;
    fetchHeritages()
      .then((data) => {
        if (active && Array.isArray(data) && data.length > 0) {
          setApiItems(data);
        }
      })
      .catch(() => {
        // Fallback sang mockData khi API chưa chạy hoặc lỗi mạng
      });
    return () => {
      active = false;
    };
  }, []);

  const sourceList: HeritageItem[] =
    apiItems.length > 0 ? (apiItems as unknown as HeritageItem[]) : fallbackMocks;

  const featuredItems = sourceList.slice(0, 10);
  const artifactItems = sourceList.slice(8, 18);
  const traditionItems = sourceList.slice(14, 24);
  const festivalItems = sourceList.slice(20, 30);

  const handleCardClick = (slug: string) => {
    router.push(`/content/${slug}`);
  };

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
