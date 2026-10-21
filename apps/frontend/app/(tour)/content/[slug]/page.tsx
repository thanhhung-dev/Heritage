"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useHeritageTour } from "@/context/heritage-tour";
import { tapestryTourVarsStyle } from "@/styles/theme/heritageTheme";
import styles from "./content-shell.module.css";
import { LogoText } from "@/components/LogoText";

/**
 * Light wordmark (175×29) — rendered as a plain `<img>` so `.sHeritageLogo`
 * alone controls its size, exactly like the Tapestry reference markup.
 */
const SPLASH_LOGO_URL =
  "https://tapestry-storage-a0fkf0afgte8hndt.z01.azurefd.net/ui-elements/logos/logo_type_light.svg";

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

const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

function formatPublishDate(value: string | null | undefined): string | null {
  if (!value) return null;
  const [year, month, day] = value.slice(0, 10).split("-");
  const monthLabel = MONTHS[Number(month) - 1];
  if (!year || !day || !monthLabel) return value;
  return `${Number(day)} ${monthLabel} ${year}`;
}


export default function ContentLoadingPage() {
  const { slug } = useParams<{ slug: string }>();
  const { payload, isModelReady, modelError } = useHeritageTour();
  const heritage = payload.heritage;
  const splashImageUrl = heritage.splash_image_url ?? "";
  const splashImageRef = useRef<HTMLImageElement>(null);
  const [loadedSplashUrl, setLoadedSplashUrl] = useState<string | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<PageLocale | null>(
    null,
  );
  const isReady = (!splashImageUrl || loadedSplashUrl === splashImageUrl) && isModelReady;
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
  const publishDate = formatPublishDate(heritage.publish_date);
  const durationLabel = heritage.duration_seconds
    ? `${Math.round(heritage.duration_seconds / 60)} min tour`
    : null;
  const presentedByLogoUrl = heritage.presented_by_logo_url;
  const availableLanguages = [heritage.language1, heritage.language2];
  const englishLanguage = availableLanguages.find((language) =>
    language?.code.toLowerCase().startsWith("en"),
  );
  const vietnameseLanguage = availableLanguages.find((language) =>
    language?.code.toLowerCase().startsWith("vi"),
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
    <main className={styles.loading} style={tapestryTourVarsStyle}>
      <div className={styles.splashWrap}>
        <img
          ref={splashImageRef}
          className={styles.splash}
          src={splashImageUrl || undefined}
          alt=""
          onLoad={finishSplashLoading}
          onError={finishSplashLoading}
        />
      </div>

      <LogoText className={styles.sHeritageLogo} size={100} />

      <div className={styles.glow} aria-hidden="true" />

      {/* Top-right badge — the sponsor logo wins over the community flag. */}
      {presentedByLogoUrl ? (
        <div className={styles.presentedBy}>
          <div className={styles.presentedByGroup}>
            <span className={styles.presentedByText}>Presented by</span>
            <img
              className={styles.presentedByLogo}
              src={presentedByLogoUrl}
              alt="Presented by"
            />
          </div>
        </div>
      ) : heritage.community_made ? (
        <div className={styles.communityMade}>
          <span className={styles.communityMadeBadge}>Community made</span>
          <span className={styles.communityMadeHover}>
            This tour was created together with the local community.
          </span>
        </div>
      ) : null}

      <div className={styles.pageGroup}>
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
            <div className={styles.aboutTour}>
              <p className={styles.aboutTourDesc}>{displayDescription}</p>
            </div>
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

          {publishDate || durationLabel ? (
            <p className={styles.publishDate}>
              {publishDate ? <span>Published {publishDate}</span> : null}
              {publishDate && durationLabel ? (
                <span className={styles.metaSep} aria-hidden="true">
                  ·
                </span>
              ) : null}
              {durationLabel ? (
                <span className={styles.manifestVersion}>{durationLabel}</span>
              ) : null}
            </p>
          ) : null}
        </section>

        <div className={styles.enterButtonGroup}>
          <Link
            className={styles.bottomNav}
            href={`/content/${slug}/s0`}
            aria-label={
              isReady
                ? "Start the heritage experience"
                : "Loading heritage assets"
            }
            aria-disabled={!isReady}
            onClick={(event) => {
              if (!isReady) event.preventDefault();
            }}
          >
            <span
              className={`${styles.loadingBarMain} ${
                isReady ? styles.loadingBarMainReady : ""
              }`}
            >
              <span className={styles.loadingBar} aria-hidden="true" />
              <span
                className={`${styles.loadingBarFill} ${
                  isReady
                    ? styles.loadingBarFillReady
                    : styles.loadingBarFillLoading
                }`}
                aria-hidden="true"
              />
              <span
                className={`${styles.loadingBarText} ${
                  isReady ? styles.loadingBarTextReady : ""
                }`}
              >
                {isReady ? "Start" : "Loading…"}
              </span>
            </span>
          </Link>

          {modelError ? (
            <p className={styles.loadingError} role="alert">{modelError}</p>
          ) : null}
        </div>
      </div>
    </main>
  );
}
