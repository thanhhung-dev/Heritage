"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { HeritageLogo } from "@/components/Logo/HeritageLogo";
import { fetchHeritagePayload } from "@/lib/heritage";
import mockHeritages from "@/mocks/heritage-mock.json";
import type {
  HeritageMediaItem,
  HeritagePayload,
  HeritageScene,
  HeritageSummary,
  HeritageVoice,
} from "@/types/heritage";

import styles from "../about.module.css";

type Locale = "en" | "vi";
type ActiveTab = "about" | "transcripts";

type GallerySlide = {
  src: string;
  thumb: string;
  title: string;
  caption: string;
  credit: string | null;
};

const copy: Record<Locale, {
  home: string;
  library: string;
  eyebrow: string;
  start: string;
  aboutTab: string;
  transcriptsTab: string;
  print: string;
  published: (year: string) => string;
  storyOutline: string;
  step: string;
  voices: string;
  gallery: string;
  galleryTitle: string;
  galleryCaption: string;
  previousImage: string;
  nextImage: string;
  aboutProject: string;
  relatedLinks: string;
  learnMore: (title: string) => string;
  credits: string;
  experienceCredit: string;
  locationCredit: string;
  subjectCredit: string;
  platformCredit: string;
  transcriptEmpty: string;
  footerTagline: string;
  footerAbout: string;
  partners: string;
  ourTeam: string;
  howItWorks: string;
  testimonials: string;
  privacy: string;
  socials: string;
  xSocial: string;
  linkedIn: string;
  tikTok: string;
  instagram: string;
  loading: string;
  unavailable: string;
}> = {
  en: {
    home: "Home",
    library: "Library",
    eyebrow: "About this experience",
    start: "Start experience",
    aboutTab: "About this experience",
    transcriptsTab: "Transcripts",
    print: "Print / Save as PDF",
    published: (year) => `Published: ${year}`,
    storyOutline: "Story outline",
    step: "Step",
    voices: "Voices",
    gallery: "Gallery",
    galleryTitle: "Gallery image",
    galleryCaption: "",
    previousImage: "Previous gallery image",
    nextImage: "Next gallery image",
    aboutProject: "About the Project",
    relatedLinks: "Related Links",
    learnMore: (title) => `Learn more about the ${title} program`,
    credits: "Credits",
    experienceCredit: "Experience",
    locationCredit: "Location",
    subjectCredit: "Subject",
    platformCredit: "Platform",
    transcriptEmpty: "Transcripts will appear here when narration is available for this experience.",
    footerTagline: "This platform is nothing without its visiting agent. Heal every story you step into.",
    footerAbout: "About HERITAGE",
    partners: "Partners",
    ourTeam: "Our team",
    howItWorks: "How it Works",
    testimonials: "Testimonials",
    privacy: "Privacy",
    socials: "Socials",
    xSocial: "X (Twitter)",
    linkedIn: "LinkedIn",
    tikTok: "TikTok",
    instagram: "Instagram",
    loading: "Loading this experience…",
    unavailable: "This experience could not be loaded.",
  },
  vi: {
    home: "Trang chủ",
    library: "Thư viện",
    eyebrow: "Về trải nghiệm này",
    start: "Bắt đầu trải nghiệm",
    aboutTab: "Về trải nghiệm",
    transcriptsTab: "Bản ghi lời dẫn",
    print: "In / Lưu PDF",
    published: (year) => `Xuất bản: ${year}`,
    storyOutline: "Nội dung câu chuyện",
    step: "Bước",
    voices: "Nhân vật",
    gallery: "Thư viện ảnh",
    galleryTitle: "Hình ảnh",
    galleryCaption: "",
    previousImage: "Ảnh trước",
    nextImage: "Ảnh tiếp theo",
    aboutProject: "Về dự án",
    relatedLinks: "Liên kết liên quan",
    learnMore: (title) => `Tìm hiểu thêm về chương trình ${title}`,
    credits: "Thông tin",
    experienceCredit: "Trải nghiệm",
    locationCredit: "Địa điểm",
    subjectCredit: "Chủ đề",
    platformCredit: "Nền tảng",
    transcriptEmpty: "Bản ghi sẽ hiển thị khi địa điểm này có lời dẫn.",
    footerTagline: "Nền tảng này không thể thiếu những người ghé thăm. Hãy khám phá từng câu chuyện.",
    footerAbout: "Về HERITAGE",
    partners: "Đối tác",
    ourTeam: "Đội ngũ",
    howItWorks: "Cách hoạt động",
    testimonials: "Đánh giá",
    privacy: "Quyền riêng tư",
    socials: "Mạng xã hội",
    xSocial: "X (Twitter)",
    linkedIn: "LinkedIn",
    tikTok: "TikTok",
    instagram: "Instagram",
    loading: "Đang tải trải nghiệm…",
    unavailable: "Không thể tải trải nghiệm này.",
  },
};

type LocalizedHeritageCopy = Partial<Pick<
  HeritageSummary,
  "title" | "tagline" | "description" | "region" | "headline"
>>;

type MockHeritageTranslation = LocalizedHeritageCopy & {
  voices?: Array<Pick<HeritageVoice, "id"> & Partial<Pick<HeritageVoice, "title" | "bio">>>;
};

const localizedHeritageCopy: Record<string, Partial<Record<Locale, LocalizedHeritageCopy>>> = {
  "tu-duc-tomb": {
    en: {
      title: "Tu Duc Tomb",
      region: "Hue, Vietnam",
      tagline: "A poetic imperial retreat in the heart of Hue",
      headline: "Discover the poetic world of Emperor Tu Duc",
      description: "Explore the architecture, landscape and stories surrounding the Tomb of Emperor Tu Duc in Hue.",
    },
    vi: {
      title: "Lăng Tự Đức",
      region: "Huế, Việt Nam",
      tagline: "Một ốc đảo thơ mộng giữa lòng Huế",
      headline: "Bước vào nơi vua Tự Đức làm thơ",
      description: "Lăng Tự Đức là khu lăng của vua Tự Đức, được xây vào thế kỷ 19.",
    },
  },
  "marble-mountains": {
    en: {
      title: "Marble Mountains",
      region: "Da Nang, Vietnam",
      tagline: "Five marble peaks between beach and river",
      headline: "Discover caves and pagodas inside the Marble Mountains.",
      description: "A cluster of five marble and limestone hills bearing caves, pagodas and Buddhist sanctuaries shaped by faith and legend, standing between the city and the sea.",
    },
    vi: {
      title: "Ngũ Hành Sơn",
      region: "Đà Nẵng, Việt Nam",
      tagline: "Năm ngọn núi đá cẩm thạch giữa biển và sông",
      headline: "Khám phá hang động và chùa chiền giữa lòng Ngũ Hành Sơn.",
      description: "Quần thể gồm năm ngọn núi đá cẩm thạch và đá vôi với nhiều hang động, chùa chiền và không gian Phật giáo gắn với tín ngưỡng cùng truyền thuyết, nằm giữa thành phố và biển.",
    },
  },
};

const localizedVoiceCopy: Record<string, { title: string; bio: string }> = {
  "Hue Heritage Guide": {
    title: "Hướng dẫn viên di sản Huế",
    bio: "Hướng dẫn viên địa phương chia sẻ những câu chuyện về di tích và cảnh quan văn hóa miền Trung Việt Nam.",
  },
  "Historian & Heritage Researcher": {
    title: "Nhà sử học và nghiên cứu di sản",
    bio: "Nhà nghiên cứu chuyên về lịch sử triều Nguyễn và di sản văn hóa Huế, Đà Nẵng.",
  },
  "Local Resident & Cultural Storyteller": {
    title: "Người dân địa phương và người kể chuyện văn hóa",
    bio: "Người kể chuyện địa phương chia sẻ góc nhìn cá nhân về di sản và đời sống văn hóa miền Trung Việt Nam.",
  },
  "Local Resident & Student": {
    title: "Người dân địa phương và sinh viên",
    bio: "",
  },
  "Tour Guide & Author": {
    title: "Hướng dẫn viên du lịch và tác giả",
    bio: "Mamoun Nawafleh là nhà nghiên cứu, tác giả người Jordan và chuyên gia về thiên văn khảo cổ tại Petra (Wadi Musa).",
  },
  "Expert in Cultural and Natural Heritage and Former Commissioner of the Petra Archaeological Reserve": {
    title: "Chuyên gia di sản văn hóa, thiên nhiên và cựu ủy viên Khu bảo tồn Khảo cổ Petra",
    bio: "",
  },
  "Former Director General of the Baptism Site Authority and Director of the Petra Reserve": {
    title: "Cựu Tổng giám đốc Cơ quan Quản lý Thánh địa Rửa tội và Giám đốc Khu bảo tồn Petra",
    bio: "",
  },
};

function getInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function getYear(publishDate: string | null, launchDate: string | null) {
  const date = publishDate ?? launchDate;
  return date ? date.slice(0, 4) : null;
}

function getGallerySlides(payload: HeritagePayload, labels: typeof copy.en): GallerySlide[] {
  const media: HeritageMediaItem[] = [
    ...(payload.overview?.media ?? []),
    ...payload.scenes.flatMap((scene) => scene.media ?? []),
  ].filter((item) => item.type.toLowerCase().includes("image"));

  if (media.length) {
    return media.map((item) => ({
      src: item.asset_url,
      thumb: item.thumb_url ?? item.asset_url,
      title: item.title ?? labels.galleryTitle,
      caption: item.caption ?? labels.galleryCaption,
      credit: item.credit,
    }));
  }

  return [...new Set([payload.heritage.card_image_url, payload.heritage.splash_image_url]
    .filter((url): url is string => Boolean(url)))].map((src) => ({
      src,
      thumb: src,
      title: labels.galleryTitle,
      caption: labels.galleryCaption,
      credit: null,
    }));
}

export default function AboutPage({ params }: { params: { slug: string } }) {
  return <AboutExperience key={params.slug} slug={params.slug} />;
}

function AboutExperience({ slug }: { slug: string }) {
  const [payload, setPayload] = useState<HeritagePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [locale, setLocale] = useState<Locale>("en");
  const [activeTab, setActiveTab] = useState<ActiveTab>("about");
  const [activeSlide, setActiveSlide] = useState(0);
  const t = copy[locale];

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(false);
    setPayload(null);

    void (async () => {
      try {
        const nextPayload = await fetchHeritagePayload(slug);
        if (!nextPayload?.heritage) throw new Error("Heritage not found");
        if (!cancelled) setPayload(nextPayload);
      } catch {
        const localHeritage = mockHeritages.find((item) => item.slug === slug);
        if (!cancelled && localHeritage) {
          const englishContent = localizedHeritageCopy[slug]?.en;
          setPayload({
            heritage: { ...localHeritage, ...englishContent } as unknown as HeritageSummary,
            overview: null,
            scenes: [],
          });
        } else if (!cancelled) {
          setLoadError(true);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [slug]);

  const gallerySlides = useMemo(
    () => payload ? getGallerySlides(payload, t) : [],
    [payload, t],
  );

  useEffect(() => {
    setActiveSlide((slide) => gallerySlides.length ? slide % gallerySlides.length : 0);
  }, [gallerySlides.length]);

  if (loading || !payload) {
    return (
      <main className={`${styles.page} ${styles.errorPage}`}>
        <div className={styles.errorCard}>
          <p className={styles.emptyState} role="status">
            {loading ? t.loading : t.unavailable}
          </p>
          {loadError ? <p className={styles.emptyState}>{slug}</p> : null}
        </div>
      </main>
    );
  }

  const heritage: HeritageSummary = payload.heritage;
  const voices: HeritageVoice[] = heritage.voices ?? [];
  const scenes: HeritageScene[] = payload.scenes ?? [];
  // Prefer translations carried in mock data; keep local copy for older API records.
  const mockTranslations = (heritage as HeritageSummary & {
    translations?: Partial<Record<Locale, MockHeritageTranslation>>;
  }).translations?.[locale];
  const translatedVoices = new Map((mockTranslations?.voices ?? []).map(({ id, ...copy }) => [id, copy]));
  const englishCopy = localizedHeritageCopy[slug]?.en;
  const vietnameseCopy = locale === "vi" ? localizedHeritageCopy[slug]?.vi : undefined;
  const localizedField = (
    key: keyof LocalizedHeritageCopy,
    value: string | null,
  ): string | null => {
    const apiTranslation = mockTranslations?.[key];
    if (apiTranslation != null) return apiTranslation;
    const translation = vietnameseCopy?.[key];
    return translation && englishCopy?.[key] === value ? translation : value;
  };
  const displayTitle = localizedField("title", heritage.title) ?? heritage.title;
  const displayRegion = localizedField("region", heritage.region);
  const displayTagline = localizedField("tagline", heritage.tagline);
  const displayHeadline = localizedField("headline", heritage.headline);
  const projectDescription = localizedField("description", heritage.description);
  const storyDescription = displayTagline ?? payload.overview?.description ?? projectDescription;
  const gallerySlide = gallerySlides[activeSlide];
  const transcriptEntries = [
    ...(payload.overview?.voice_clips ?? []),
    ...scenes.flatMap((scene) => scene.voice_clips ?? []),
  ].filter((clip) => clip.bubble_text);
  const year = getYear(heritage.publish_date, heritage.launch_date);
  const heroImage = heritage.splash_image_url ?? heritage.card_image_url;
  const aboutHref = `/about/${encodeURIComponent(slug)}`;

  const moveGallery = (direction: -1 | 1) => {
    setActiveSlide((current) => gallerySlides.length
      ? (current + direction + gallerySlides.length) % gallerySlides.length
      : 0);
  };

  return (
    <div className={styles.page}>
      <a className={styles.skipLink} href="#about-main">
        {locale === "en" ? "Skip to content" : "Bỏ qua đến nội dung"}
      </a>

      <header className={styles.siteHeader}>
        <Link className={styles.brand} href="/" aria-label="HERITAGE — Home">
          <HeritageLogo size={23} />
          <span>HERITAGE</span>
        </Link>
        <nav className={styles.siteNav} aria-label={locale === "en" ? "Main navigation" : "Điều hướng chính"}>
          <Link href="/">{t.home}</Link>
          <Link href="/library">{t.library}</Link>
        </nav>
      </header>

      <section className={styles.hero} aria-labelledby="experience-title">
        {heroImage ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img className={styles.heroImage} src={heroImage} alt="" />
        ) : null}
        <div className={styles.heroShade} aria-hidden="true" />
        <div className={styles.heroContent}>
          <p className={styles.eyebrow}>{t.eyebrow}</p>
          <h1 id="experience-title">{displayTitle}</h1>
          {displayRegion ? <p className={styles.heroLocation}>{displayRegion}</p> : null}
          <Link className={styles.startButton} href={`/content/${encodeURIComponent(slug)}/s0`}>
            {t.start}
          </Link>
        </div>
      </section>

      <div className={styles.contentTabs}>
        <div className={styles.tabsInner}>
          <div className={styles.tabsGroup} role="tablist" aria-label={locale === "en" ? "Experience information" : "Thông tin trải nghiệm"}>
            <button
              className={activeTab === "about" ? styles.tabActive : styles.tab}
              id="about-tab"
              type="button"
              role="tab"
              aria-selected={activeTab === "about"}
              aria-controls="about-panel"
              onClick={() => setActiveTab("about")}
            >
              {t.aboutTab}
            </button>
            <button
              className={activeTab === "transcripts" ? styles.tabActive : styles.tab}
              id="transcripts-tab"
              type="button"
              role="tab"
              aria-selected={activeTab === "transcripts"}
              aria-controls="about-panel"
              onClick={() => setActiveTab("transcripts")}
            >
              {t.transcriptsTab}
            </button>
          </div>

          <div className={styles.tabActions}>
            <div className={styles.languageSwitch} aria-label={locale === "en" ? "Language" : "Ngôn ngữ"}>
              <button
                className={locale === "en" ? styles.languageActive : styles.language}
                type="button"
                aria-pressed={locale === "en"}
                onClick={() => setLocale("en")}
              >English</button>
              <button
                className={locale === "vi" ? styles.languageActive : styles.language}
                type="button"
                aria-pressed={locale === "vi"}
                onClick={() => setLocale("vi")}
              >Vietnamese</button>
            </div>
            <button className={styles.printButton} type="button" onClick={() => window.print()}>
              {t.print}
            </button>
          </div>
        </div>
      </div>

      <main className={styles.main} id="about-main" tabIndex={-1}>
        <div className={styles.articleMeta}>
          {year ? <p>{t.published(year)}</p> : null}
        </div>

        <section
          className={styles.article}
          id="about-panel"
          role="tabpanel"
          aria-labelledby={activeTab === "about" ? "about-tab" : "transcripts-tab"}
          tabIndex={0}
        >
          {activeTab === "about" ? (
            <>
              <section className={styles.storySection} aria-labelledby="story-heading">
                <h2 id="story-heading">{t.storyOutline}</h2>
                {payload.overview || heritage.description || heritage.tagline ? (
                  <div className={styles.storyIntro}>
                    <h3>{displayTitle}</h3>
                    {storyDescription ? <p>{storyDescription}</p> : null}
                  </div>
                ) : null}
                {scenes.length ? (
                  <ol className={styles.storySteps}>
                    {scenes.map((scene, index) => (
                      <li key={scene.id}>
                        <h3>
                          <span className={styles.stepNumber}>{t.step} {index + 1}.</span>{" "}
                          {scene.title}
                        </h3>
                        {scene.description ? <p>{scene.description}</p> : null}
                      </li>
                    ))}
                  </ol>
                ) : null}
              </section>

              {voices.length ? (
                <section className={styles.voicesSection} aria-labelledby="voices-heading">
                  <h2 id="voices-heading">{t.voices}</h2>
                  <ul className={styles.voiceList}>
                    {voices.map((voice, index) => (
                      <li className={styles.voice} key={voice.id}>
                        <span className={`${styles.voiceAvatar} ${styles[`voiceAvatar${index % 4}`]}`} aria-hidden="true">
                          {getInitials(voice.name)}
                          {voice.headshot_url ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={voice.headshot_url} alt="" onError={(event) => { event.currentTarget.style.display = "none"; }} />
                          ) : null}
                        </span>
                        <span className={styles.voiceText}>
                          <strong>{voice.name}</strong>
                          {voice.title ? (
                            <span className={styles.voiceTitle}>
                              {locale === "vi"
                                ? translatedVoices.get(voice.id)?.title
                                  ?? localizedVoiceCopy[voice.title]?.title
                                  ?? voice.title
                                : voice.title}
                            </span>
                          ) : null}
                          {voice.bio ? (
                            <span className={styles.voiceBio}>
                              {locale === "vi"
                                ? translatedVoices.get(voice.id)?.bio
                                  ?? localizedVoiceCopy[voice.title ?? ""]?.bio
                                  ?? voice.bio
                                : voice.bio}
                            </span>
                          ) : null}
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {gallerySlides.length ? (
                <section className={styles.gallerySection} aria-labelledby="gallery-heading">
                  <h2 id="gallery-heading">{t.gallery}</h2>
                  {gallerySlide ? (
                    <>
                      <div className={styles.galleryFrame}>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img className={styles.galleryImage} src={gallerySlide.src} alt={gallerySlide.title} />
                      </div>
                      <div className={styles.galleryControls}>
                        <button className={styles.galleryArrow} type="button" aria-label={t.previousImage} onClick={() => moveGallery(-1)}>
                          <span aria-hidden="true">‹</span>
                        </button>
                        <h3>{gallerySlide.title}</h3>
                        <button className={styles.galleryArrow} type="button" aria-label={t.nextImage} onClick={() => moveGallery(1)}>
                          <span aria-hidden="true">›</span>
                        </button>
                      </div>
                      {gallerySlide.caption ? <p className={styles.galleryCaption}>{gallerySlide.caption}</p> : null}
                      {gallerySlide.credit ? <p className={styles.galleryCredit}>{gallerySlide.credit}</p> : null}
                      {gallerySlides.length > 1 ? (
                        <div className={styles.thumbnailRail} aria-label={t.gallery}>
                          {gallerySlides.map((slide, index) => (
                            <button
                              className={index === activeSlide ? styles.thumbnailActive : styles.thumbnail}
                              type="button"
                              key={`${slide.src}-${index}`}
                              aria-label={`${slide.title}, ${index + 1}/${gallerySlides.length}`}
                              aria-pressed={index === activeSlide}
                              onClick={() => setActiveSlide(index)}
                            >
                              {/* eslint-disable-next-line @next/next/no-img-element */}
                              <img src={slide.thumb} alt="" />
                            </button>
                          ))}
                        </div>
                      ) : null}
                    </>
                  ) : null}
                </section>
              ) : null}

              {projectDescription ? (
                <section className={styles.projectSection} id="project-heading" aria-labelledby="project-heading-label">
                  <h2 id="project-heading-label">{t.aboutProject}</h2>
                  <p>{projectDescription}</p>
                </section>
              ) : null}

              {projectDescription ? (
                <section className={styles.textSection} aria-labelledby="links-heading">
                  <h2 id="links-heading">{t.relatedLinks}</h2>
                  <ul>
                    <li><Link href="#project-heading">{t.learnMore(displayTitle)}</Link></li>
                  </ul>
                </section>
              ) : null}

              <section className={styles.textSection} aria-labelledby="credits-heading">
                <h2 id="credits-heading">{t.credits}</h2>
                <p>{t.experienceCredit}: {displayTitle}</p>
                {displayRegion ? <p>{t.locationCredit}: {displayRegion}</p> : null}
                {(displayTagline || displayHeadline) ? <p>{t.subjectCredit}: {displayTagline ?? displayHeadline}</p> : null}
                <p>{t.platformCredit}: HeritageGraph</p>
              </section>

            </>
          ) : transcriptEntries.length ? (
            <section className={styles.transcriptList} aria-label={t.transcriptsTab}>
              {transcriptEntries.map((entry) => (
                <article className={styles.transcript} key={entry.id}>
                  <h2>{entry.voice.name}</h2>
                  <p>{entry.bubble_text}</p>
                </article>
              ))}
            </section>
          ) : (
            <p className={styles.emptyState}>{t.transcriptEmpty}</p>
          )}
        </section>
      </main>

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <div className={styles.footerBrandColumn}>
            <Link className={styles.footerBrand} href="/" aria-label="HERITAGE — Home">
              <HeritageLogo size={22} />
              <span>HERITAGE</span>
            </Link>
            <p>{t.footerTagline}</p>
          </div>
          <div className={styles.footerColumn}>
            <h2>{t.footerAbout}</h2>
            <Link href="/library">{t.partners}</Link>
            <Link href={`${aboutHref}#voices-heading`}>{t.ourTeam}</Link>
            <Link href={`${aboutHref}#story-heading`}>{t.howItWorks}</Link>
            <Link href="/library">{t.testimonials}</Link>
            <Link href="/">{t.privacy}</Link>
          </div>
          <div className={styles.footerColumn}>
            <h2>{t.socials}</h2>
            <a href="https://x.com" target="_blank" rel="noreferrer">{t.xSocial}</a>
            <a href="https://www.linkedin.com" target="_blank" rel="noreferrer">{t.linkedIn}</a>
            <a href="https://www.tiktok.com" target="_blank" rel="noreferrer">{t.tikTok}</a>
            <a href="https://www.instagram.com" target="_blank" rel="noreferrer">{t.instagram}</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
