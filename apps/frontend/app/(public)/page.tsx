"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  HeroSection,
  DiscoverMoreSection,
  HeritageCarouselSection,
  HeritageInfoModal,
  getCardImageUrl,
  selectFeaturedTriptychItems,
  type HeritageItem,
} from "@/features/home";
import type { TriptychCardData } from "@/components/TriptychCard/TriptychCard";
import { getHeritages } from "@/services/heritage.service";
import ContentLoading from "@/components/Loading/ContentLoading";

const FALLBACK_HERITAGE_ITEMS: any[] = [
  {
    id: 1,
    slug: "lang-tu-duc",
    title: "Lăng Tự Đức",
    region: "Huế",
    card_image_url:
      "https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?auto=format&fit=crop&w=1200&q=80",
    splash_image_url:
      "https://images.unsplash.com/photo-1599707367072-cd6ada2bc375?auto=format&fit=crop&w=1200&q=80",
    hover_video_url: "/tuc-duc-hover.mp4",
    publish_date: "2025-01-01T00:00:00Z",
    language1: { name: "Vietnamese" },
    description:
      "Khám phá Khiêm Lăng, công trình gắn liền với vua Tự Đức, thông qua không gian 3D, văn bia Khiêm Cung Ký và khu lăng mộ.",
    voices: [
      {
        id: 101,
        name: "Ngọc Ngân",
        title: "Người thuyết minh tiếng Việt",
        headshot_url:
          "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&h=100&q=80",
      },
      {
        id: 102,
        name: "Hung Heo",
        title: "Cultural Interpreter, Musician",
        headshot_url:
          "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=100&h=100&q=80",
      },
      {
        id: 103,
        name: "Hung Heo",
        title: "Cultural Interpreter, Dancer",
        headshot_url:
          "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=100&h=100&q=80",
      },
    ],
  },
  {
    id: 2,
    slug: "cung-an-dinh",
    title: "Cung An Định",
    region: "Huế",
    card_image_url:
      "https://images.unsplash.com/photo-1583417319070-4a69db38a482?auto=format&fit=crop&w=1200&q=80",
    splash_image_url:
      "https://images.unsplash.com/photo-1583417319070-4a69db38a482?auto=format&fit=crop&w=1200&q=80",
    publish_date: "2025-01-01T00:00:00Z",
    language1: { name: "Vietnamese" },
    description:
      "Cung An Định được vua Khải Định cho xây dựng đầu thế kỷ 20 bên bờ sông An Cựu, mang kiến trúc cung đình kết hợp phong cách châu Âu. Sau này cung gắn liền với cuộc đời Nam Phương hoàng hậu – vị hoàng hậu cuối cùng của Việt Nam.",
    voices: [
      {
        id: 201,
        name: "Hung Heo",
        title: "Former Museum Curator",
        headshot_url:
          "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&h=100&q=80",
      },
      {
        id: 202,
        name: "Hung Heo",
        title: "Cultural Interpreter, Musician",
        headshot_url:
          "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=100&h=100&q=80",
      },
      {
        id: 203,
        name: "Hung Heo",
        title: "Cultural Interpreter, Dancer",
        headshot_url:
          "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=100&h=100&q=80",
      },
    ],
  },
  {
    id: 3,
    slug: "ngu-hanh-son",
    title: "Ngũ Hành Sơn",
    region: "Đà Nẵng",
    card_image_url:
      "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1200&q=80",
    splash_image_url:
      "https://images.unsplash.com/photo-1528127269322-539801943592?auto=format&fit=crop&w=1200&q=80",
    publish_date: "2025-01-01T00:00:00Z",
    language1: { name: "Vietnamese" },
    description:
      "Quần thể gồm sáu ngọn núi đá vôi nhô lên trên một bãi cát ven biển, nổi tiếng với các hang động huyền bí và làng đá mỹ nghệ truyền thống Non Nước.",
    voices: [
      {
        id: 301,
        name: "Hung Heo",
        title: "Former Museum Curator",
        headshot_url:
          "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=100&h=100&q=80",
      },
      {
        id: 302,
        name: "Hung Heo",
        title: "Cultural Interpreter, Musician",
        headshot_url:
          "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=100&h=100&q=80",
      },
      {
        id: 303,
        name: "Hung Heo",
        title: "Cultural Interpreter, Dancer",
        headshot_url:
          "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=100&h=100&q=80",
      },
    ],
  },
];

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

  const sourceList = (apiItems.length > 0 ? apiItems : FALLBACK_HERITAGE_ITEMS) as unknown as HeritageItem[];

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
          backgroundColor: "#07090e",
        }}
      >
     <ContentLoading label="Loading heritage experiences..." />
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
        backgroundColor: "#07090e",
      }}
    >
      <HeroSection
        items={apiItems.length > 0 ? apiItems : (FALLBACK_HERITAGE_ITEMS as any)}
        loading={false}
        onInfo={handleOpenInfoModal}
      />

      <HeritageCarouselSection
        title="Featured Experiences"
        description="Curated virtual journeys and immersive stories"
        items={featuredItems}
        onCardClick={handleOpenInfoModal}
      />

      <HeritageCarouselSection
        title="Artifacts & Treasures"
        description="The tools, art, and objects that shape human history"
        items={artifactItems}
        onCardClick={handleOpenInfoModal}
      />

      <HeritageCarouselSection
        title="People & Traditions"
        description="Community members share personal stories and memories"
        items={traditionItems}
        onCardClick={handleOpenInfoModal}
      />

      <HeritageCarouselSection
        title="Festivals & Community Practices"
        description="The rituals and customs that bring heritage to life"
        items={festivalItems}
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