"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { useHeritageTour } from "@/context/heritage-tour";
import styles from "./content-shell.module.css";

type PageLocale = "en" | "vi";

type LocalizedPageCopy = {
  region: string;
  title: string;
  headline: string;
  tagline: string;
  description: string;
};

const TU_DUC_COPY: Record<PageLocale, LocalizedPageCopy> = {
  en: {
    region: "Hue, Vietnam",
    title: "Tu Duc Tomb",
    headline: "Discover the poetic world of Emperor Tu Duc",
    tagline: "A poetic imperial retreat in the heart of Hue",
    description:
      "Explore the architecture, landscape and stories surrounding the Tomb of Emperor Tu Duc in Hue.",
  },
  vi: {
    region: "Huế, Việt Nam",
    title: "Lăng Tự Đức",
    headline: "Bước vào nơi vua Tự Đức làm thơ",
    tagline: "Một ốc đảo thơ mộng giữa lòng Huế",
    description:
      "Lăng Tự Đức là khu lăng của vua Tự Đức, được xây vào thế kỷ 19.",
  },
};

const LOCALIZED_COPY: Record<string, Record<PageLocale, LocalizedPageCopy>> = {
  demo: TU_DUC_COPY,
  "tu-duc-tomb": TU_DUC_COPY,
};

/**
 * `/content/{slug}` — fullscreen heritage loading screen.
 * The background and copy are rendered from the heritage payload while the
 * tour scene prepares; activating the loading bar opens the first scene.
 */
export default function ContentLoadingPage() {
  const { slug } = useParams<{ slug: string }>();
  const { payload } = useHeritageTour();
  const heritage = payload.heritage;
  const splashImageUrl = heritage.splash_image_url ?? "";
  const splashImageRef = useRef<HTMLImageElement>(null);
  const [loadedSplashUrl, setLoadedSplashUrl] = useState<string | null>(null);
  const [selectedLanguage, setSelectedLanguage] =
    useState<PageLocale | null>(null);
  const isReady = !splashImageUrl || loadedSplashUrl === splashImageUrl;
  const sourceLanguage: PageLocale = heritage.language1?.code
    .toLowerCase()
    .startsWith("vi")
    ? "vi"
    : "en";
  const displayLanguage = selectedLanguage ?? sourceLanguage;
  const translatedCopy = LOCALIZED_COPY[heritage.slug]?.[displayLanguage];
  const displayRegion = translatedCopy?.region ?? heritage.region;
  const displayTitle =
    translatedCopy?.headline ??
    translatedCopy?.title ??
    heritage.headline ??
    heritage.title ??
    slug;
  const displayTagline = translatedCopy?.tagline ?? heritage.tagline;
  const displayDescription =
    translatedCopy?.description ?? heritage.description;
  const availableLanguages = [heritage.language1, heritage.language2];
  const englishLanguage = availableLanguages.find((language) =>
    language?.code.toLowerCase().startsWith("en")
  );
  const vietnameseLanguage = availableLanguages.find((language) =>
    language?.code.toLowerCase().startsWith("vi")
  );
  const languages = [
    {
      code: "en" as const,
      name: englishLanguage?.name ?? "English",
    },
    {
      code: "vi" as const,
      name: vietnameseLanguage?.name ?? "Vietnamese",
    },
  ];

  useEffect(() => {
    if (splashImageRef.current?.complete && splashImageUrl) {
      setLoadedSplashUrl(splashImageUrl);
    }
  }, [splashImageUrl]);

  const finishSplashLoading = () => {
    if (splashImageUrl) setLoadedSplashUrl(splashImageUrl);
  };

  return (
    <main className={styles.loading}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        ref={splashImageRef}
        className={styles.splash}
        src={splashImageUrl || undefined}
        alt=""
        onLoad={finishSplashLoading}
        onError={finishSplashLoading}
      />
      <div className={styles.scrim} aria-hidden="true" />

      <div className={styles.brand} role="img" aria-label="Heritage">
        <span className={styles.brandMark} aria-hidden="true" />
        <span className={styles.brandName}>HERITAGE</span>
      </div>

      <section className={styles.infoCard} aria-labelledby="heritage-title">
        {displayRegion ? (
          <p className={styles.region}>{displayRegion}</p>
        ) : null}
        <h1 className={styles.title} id="heritage-title">
          {displayTitle}
        </h1>
        {displayTagline ? (
          <p className={styles.subtitle}>{displayTagline}</p>
        ) : null}
        {displayDescription ? (
          <p className={styles.description}>{displayDescription}</p>
        ) : null}

        <div className={styles.languages} aria-label="Available languages">
          {languages.map((language) => (
            <button
              className={
              language.code === displayLanguage
                  ? styles.languageActive
                  : styles.language
              }
              key={language.code}
              type="button"
              aria-pressed={language.code === displayLanguage}
              onClick={() => setSelectedLanguage(language.code)}
            >
              {language.name}
            </button>
          ))}
        </div>
      </section>

      <Link
        className={`${styles.action} ${
          isReady ? styles.startAction : styles.loadingAction
        }`}
        href={`/content/${slug}/s0`}
        aria-label={
          isReady ? "Start the heritage experience" : "Loading heritage assets"
        }
        aria-disabled={!isReady}
        onClick={(event) => {
          if (!isReady) event.preventDefault();
        }}
      >
        {!isReady ? (
          <span className={styles.loadingProgress} aria-hidden="true" />
        ) : null}
        <span className={styles.actionLabel}>
          {isReady ? "START" : "LOADING..."}
        </span>
      </Link>
    </main>
  );
}
