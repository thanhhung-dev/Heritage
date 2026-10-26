"use client";

import {
  HeroSection,
  DiscoverMoreSection,
  HeritageCarouselSection,
  type HeritageItem,
} from "@/features/home";
import mockData from "@/mocks/heritage-mock.json";

export default function HeritagePreviewPage() {
  const allMocks = mockData as unknown as HeritageItem[];

  const featuredItems = allMocks.slice(0, 10);
  const artifactItems = allMocks.slice(8, 18);
  const traditionItems = allMocks.slice(14, 24);
  const festivalItems = allMocks.slice(20, 30);

  const handleCardClick = (slug: string) => {
    window.alert(`Mở chi tiết di sản: ${slug}`);
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
      {/* 1. HeroSection */}
      <HeroSection onInfo={handleCardClick} />

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
