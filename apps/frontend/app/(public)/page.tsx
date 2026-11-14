"use client";

import { useEffect, useMemo, useState } from "react";
import { Avatar, Button, ConfigProvider, Modal, theme } from "antd";
import {
  HeroSection,
  FEATURED_HERO_SLUGS,
  DiscoverMoreSection,
  HeritageCarouselSection,
  HeritageInfoModal,
  type HeritageItem,
} from "@/features/home";
import {
  getHeritages,
  type HeritageItem as HeritageRecord,
} from "@/services/heritage.service";
import styles from "@/features/home/HeritageCarouselSection.module.css";

// Curated groups for the published heritage list, which has no category field.
const ARTIFACT_HERITAGE_SLUGS = new Set([
  "cuu-dinh",
  "bao-tang-dieu-khac-cham",
]);

const FESTIVAL_HERITAGE_SLUGS = new Set([
  "dien-hon-chen",
  "lang-sinh",
  "cau-ngoi-thanh-toan",
  "ngu-hanh-son",
  "dinh-lang-tuy-loan",
  "dinh-lang-nam-o",
  "pho-co-hoi-an",
  "lang-gom-thanh-ha",
  "lang-da-non-nuoc",
]);

function toFeaturedCard(item: HeritageRecord): HeritageItem {
  const year = item.publish_date ? new Date(item.publish_date).getUTCFullYear() : NaN;

  return {
    slug: item.slug,
    title: item.title,
    region: item.region,
    description: item.description,
    card_image_url: item.card_image_url || item.splash_image_url,
    published: Number.isFinite(year) ? `Published ${year}` : null,
    language_label: item.language1?.name || "",
    href: `/content/${encodeURIComponent(item.slug)}`,
  };
}

function toPeopleCards(heritages: HeritageRecord[]): HeritageItem[] {
  const people = new Map<string, HeritageItem>();

  for (const heritage of heritages) {
    for (const voice of Array.isArray(heritage.voices) ? heritage.voices : []) {
      if (!voice.name?.trim()) continue;
      const key = voice.id != null
        ? `voice-${voice.id}`
        : `${heritage.slug}-${voice.name}`;
      if (people.has(key)) continue;

      people.set(key, {
        slug: key,
        kind: "person",
        title: voice.name,
        region: voice.title,
        description: voice.bio,
        card_image_url: voice.headshot_url,
        href: `/content/${encodeURIComponent(heritage.slug)}`,
        heritageTitle: heritage.title,
      });
    }
  }

  return Array.from(people.values());
}

export default function HomePage() {
  const [apiItems, setApiItems] = useState<HeritageRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [modalItem, setModalItem] = useState<HeritageRecord | null>(null);
  const [selectedPerson, setSelectedPerson] = useState<HeritageItem | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(false);

    getHeritages()
      .then((data) => {
        if (!Array.isArray(data)) throw new Error("Invalid heritage list");
        if (!active) return;
        setApiItems(data.filter((item) => item && item.slug && item.title));
      })
      .catch(() => {
        if (active) setError(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [attempt]);

  useEffect(() => {
    if (!error) return;
    const retry = () => {
      if (document.visibilityState === "visible") setAttempt((value) => value + 1);
    };
    const timer = window.setTimeout(retry, 30_000);
    window.addEventListener("online", retry);
    window.addEventListener("focus", retry);

    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("online", retry);
      window.removeEventListener("focus", retry);
    };
  }, [error, attempt]);

  const featuredItems = useMemo(() => apiItems.map(toFeaturedCard), [apiItems]);
  const artifactItems = useMemo(
    () => featuredItems.filter((item) => ARTIFACT_HERITAGE_SLUGS.has(item.slug)),
    [featuredItems],
  );
  const peopleItems = useMemo(() => toPeopleCards(apiItems), [apiItems]);
  const festivalItems = useMemo(
    () => featuredItems.filter((item) => FESTIVAL_HERITAGE_SLUGS.has(item.slug)),
    [featuredItems],
  );
  const tuDucCard = featuredItems.find((item) =>
    FEATURED_HERO_SLUGS[0].some((slug) => slug === item.slug),
  );
  const backdropUrl = tuDucCard?.card_image_url;

  const openHeritageInfo = (slug: string) => {
    setModalItem(apiItems.find((item) => item.slug === slug) ?? null);
  };
  const retry = () => setAttempt((value) => value + 1);
  const apiError = error
    ? "Chưa tải được nội dung. Trang sẽ thử kết nối lại khi máy chủ sẵn sàng."
    : undefined;

  return (
    <div className={styles.homePage}>
      <HeroSection items={apiItems} loading={loading} onInfo={openHeritageInfo} />

      <div className={styles.carouselGroup}>
        {backdropUrl && (
          <div
            className={styles.carouselGroupImage}
            style={{ backgroundImage: `url(${JSON.stringify(backdropUrl)})` }}
            aria-hidden="true"
          />
        )}
        <HeritageCarouselSection
          title="Featured Experiences"
          description="Curated selection of our favorite Tapestry experiences"
          items={featuredItems}
          sharedBackdrop
          loading={loading}
          error={apiError}
          onRetry={retry}
          onCardClick={openHeritageInfo}
          emptyMessage="Chưa có trải nghiệm di sản được xuất bản."
        />

        <HeritageCarouselSection
          title="Artifacts & Treasures"
          description="The tools, art, and objects that shape human history"
          items={artifactItems}
          sharedBackdrop
          loading={loading}
          error={apiError}
          onRetry={retry}
          onCardClick={openHeritageInfo}
          emptyMessage="Chưa có nội dung hiện vật và bảo vật."
        />

        <HeritageCarouselSection
          title="People & Traditions"
          description="Community members share their personal stories and memories"
          items={peopleItems}
          sharedBackdrop
          loading={loading}
          error={apiError}
          onRetry={retry}
          onCardClick={(key) => {
            setSelectedPerson(peopleItems.find((item) => item.slug === key) ?? null);
          }}
          emptyMessage="Chưa có câu chuyện từ nhân vật và cộng đồng."
        />

        <HeritageCarouselSection
          title="Festivals & Community Practices"
          description="Discover festivals and traditions through the places that keep them alive"
          className={styles.festivalSection}
          items={festivalItems}
          sharedBackdrop
          loading={loading}
          error={apiError}
          onRetry={retry}
          onCardClick={openHeritageInfo}
          emptyMessage="Chưa có nội dung lễ hội và sinh hoạt cộng đồng."
        />
      </div>

      <DiscoverMoreSection />
      <HeritageInfoModal item={modalItem} onClose={() => setModalItem(null)} />

      <ConfigProvider theme={{
        algorithm: theme.darkAlgorithm,
        token: { colorPrimary: "#ff9b2d", fontFamily: "Poppins, sans-serif" },
      }}>
        <Modal
          open={selectedPerson !== null}
          title={selectedPerson?.title}
          onCancel={() => setSelectedPerson(null)}
          footer={selectedPerson?.href ? (
            <Button type="primary" href={selectedPerson.href}>
              Khám phá {selectedPerson.heritageTitle}
            </Button>
          ) : null}
          centered
          destroyOnHidden
        >
          {selectedPerson && (
            <div className={styles.personDetail}>
              <Avatar
                shape="square"
                size={96}
                src={selectedPerson.card_image_url || undefined}
                alt={selectedPerson.title}
              >
                {selectedPerson.title.split(/\s+/).slice(0, 2).map((part) => part[0]).join("")}
              </Avatar>
              {selectedPerson.region && <p className={styles.personRole}>{selectedPerson.region}</p>}
              <p>{selectedPerson.description || "Chưa có phần giới thiệu nhân vật."}</p>
            </div>
          )}
        </Modal>
      </ConfigProvider>
    </div>
  );
}
