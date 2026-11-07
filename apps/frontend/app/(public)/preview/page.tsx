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

export default function HeritagePreviewPage() {
  const router = useRouter();

  const [apiItems, setApiItems] = useState<TriptychCardData[]>([]);

  useEffect(() => {
    let active = true;
    fetchHeritages()
      .then((data) => {
        if (active && Array.isArray(data)) {
          setApiItems(data);
        }
      })
      .catch(() => {
        // API lỗi ⇒ để trống, các section tự ẩn. Không còn dữ liệu mock thay thế.
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
      {/* 1. HeroSection (3 Featured Cards: Lăng Tự Đức, Cung An Định, Ngũ Hành Sơn) */}
      <HeroSection
        items={apiItems.length > 0 ? apiItems : undefined}
        onInfo={handleCardClick}
      />

      {/* 2. Featured Experiences Carousel */}
      <HeritageCarouselSection
        title="Featured Experiences"
        description="Curated virtual journeys and immersive stories"
        items={featuredItems}
        onCardClick={handleCardClick}
      />

      {/* 3. Artifacts & Treasures Carousel */}
      <HeritageCarouselSection
        title="Artifacts & Treasures"
        description="The tools, art, and objects that shape human history"
        items={artifactItems}
        onCardClick={handleCardClick}
      />

      {/* 4. People & Traditions Carousel */}
      <HeritageCarouselSection
        title="People & Traditions"
        description="Community members share personal stories and memories"
        items={traditionItems}
        onCardClick={handleCardClick}
      />

      {/* 5. Festivals & Community Practices Carousel */}
      <HeritageCarouselSection
        title="Festivals & Community Practices"
        description="The rituals and customs that bring heritage to life"
        items={festivalItems}
        onCardClick={handleCardClick}
      />

      {/* 6. Discover More CTA Section */}
      <DiscoverMoreSection />
    </div>
  );
}
