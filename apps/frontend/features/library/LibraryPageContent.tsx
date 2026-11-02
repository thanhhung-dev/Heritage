"use client";

import { useEffect, useState, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  PortraitCard,
  type PortraitCardData,
} from "@/components/PortraitCard/PortraitCard";
import { Pagination } from "@/components/Pagination/Pagination";
import { fetchHeritages } from "@/lib/heritage";
import type { HeritageSummary } from "@/types/heritage";
import styles from "./library.module.css";

const DEFAULT_HERO_BG =
  "https://tapestry-storage-a0fkf0afgte8hndt.z01.azurefd.net/petra-data/petra_card_2-1080x608.webp";

export function LibraryPageContent() {
  const router = useRouter();

  const [items, setItems] = useState<HeritageSummary[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [query, setQuery] = useState("");
  const [region, setRegion] = useState("");
  const [language, setLanguage] = useState("");
  const [order, setOrder] = useState<"newest" | "oldest">("newest");
  const [page, setPage] = useState(1);
  const [attempt, setAttempt] = useState(0);

  const [isScrolled, setIsScrolled] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<"category" | "language" | null>(
    null
  );

  const categoryDropdownRef = useRef<HTMLDivElement>(null);
  const languageDropdownRef = useRef<HTMLDivElement>(null);

  // Restore filter state from URL parameters
  useEffect(() => {
    const restore = () => {
      const params = new URLSearchParams(window.location.search);
      setQuery(params.get("q") ?? "");
      setRegion(params.get("region") ?? "");
      setLanguage(params.get("language") ?? "");
      setOrder(params.get("order") === "oldest" ? "oldest" : "newest");
      const number = Number(params.get("page"));
      setPage(Number.isSafeInteger(number) && number > 0 ? number : 1);
    };
    restore();
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);

  // Sticky filterbar scroll listener
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Close dropdown on outside click or escape key
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        openDropdown === "category" &&
        categoryDropdownRef.current &&
        !categoryDropdownRef.current.contains(target)
      ) {
        setOpenDropdown(null);
      }
      if (
        openDropdown === "language" &&
        languageDropdownRef.current &&
        !languageDropdownRef.current.contains(target)
      ) {
        setOpenDropdown(null);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpenDropdown(null);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [openDropdown]);

  // Sync state changes with URL query string
  function updateUrl(key: string, value: string, replace = false) {
    const url = new URL(window.location.href);
    if (value) url.searchParams.set(key, value);
    else url.searchParams.delete(key);
    if (key !== "page") url.searchParams.delete("page");
    window.history[replace ? "replaceState" : "pushState"](null, "", url);
  }

  // Clear all filters
  const handleClearAll = () => {
    setQuery("");
    setRegion("");
    setLanguage("");
    setOrder("newest");
    setPage(1);
    const url = new URL(window.location.href);
    ["q", "region", "language", "order", "page"].forEach((key) =>
      url.searchParams.delete(key)
    );
    window.history.pushState(null, "", url);
  };

  // Fetch heritages data
  useEffect(() => {
    let active = true;
    setStatus("loading");
    fetchHeritages()
      .then((data) => {
        if (!Array.isArray(data)) throw new Error("Invalid heritage list");
        if (active) {
          setItems(data);
          setStatus("ready");
        }
      })
      .catch(() => {
        if (active) setStatus("error");
      });
    return () => {
      active = false;
    };
  }, [attempt]);

  // Distinct category/region counts
  const categoryCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of items) {
      if (item.region) {
        counts.set(item.region, (counts.get(item.region) || 0) + 1);
      }
    }
    return Array.from(counts.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [items]);

  // Distinct language counts
  const languageCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of items) {
      const langs = [item.language1?.name, item.language2?.name].filter(
        Boolean
      ) as string[];
      for (const lang of langs) {
        counts.set(lang, (counts.get(lang) || 0) + 1);
      }
    }
    return Array.from(counts.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [items]);

  // Filter and sort items
  const filtered = useMemo(() => {
    return items
      .filter((item) => {
        const text = `${item.title} ${item.region ?? ""}`.toLocaleLowerCase();
        const matchesQuery = text.includes(query.trim().toLocaleLowerCase());
        const matchesRegion = !region || item.region === region;
        const matchesLanguage =
          !language ||
          [item.language1?.name, item.language2?.name].includes(language);
        return matchesQuery && matchesRegion && matchesLanguage;
      })
      .sort((a, b) => {
        const left = a.publish_date;
        const right = b.publish_date;
        if (!left) return right ? 1 : 0;
        if (!right) return -1;
        return order === "newest"
          ? right.localeCompare(left)
          : left.localeCompare(right);
      });
  }, [items, query, region, language, order]);

  // Pagination calculation
  const PAGE_SIZE = 24;
  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const currentPage = Math.min(page, Math.max(totalPages, 1));
  const visibleItems = filtered.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  const hasActiveFilters = Boolean(
    query.trim() || region || language || order !== "newest"
  );

  const heroBgImage =
    items[0]?.splash_image_url || items[0]?.card_image_url || DEFAULT_HERO_BG;

  return (
    <div className={styles.libraryPage}>
      {/* 1. Cinematic Slim Hero Header */}
      <header className={styles.library_hero_slim} id="library_hero">
        <div className={styles.hp_hero_bg_layers} id="library_hero_bg_layers">
          <div
            className={`${styles.hp_hero_bg_layer} ${styles.hp_hero_bg_layer_active}`}
            style={{ backgroundImage: `url(${heroBgImage})` }}
          />
        </div>
        <div className={`${styles.hp_hero_overlay} ${styles.library_hero_overlay}`} />
        <div className={styles.hp_hero_grain} />

        <div className={styles.library_hero_center}>
          <h1 className={styles.library_hero_title}>HERITAGE Virtual Tours</h1>
          <p className={styles.library_hero_subtitle} id="library_hero_subtitle">
            Discover our library of {items.length > 0 ? items.length : 78} immersive experiences
          </p>
        </div>
      </header>

      {/* 2. Sticky Filter Bar */}
      <div
        className={`${styles.library_filterbar} ${isScrolled ? styles.scrolled : ""}`}
        id="library_filterbar"
      >
        <div className={styles.library_filterbar_inner}>
          <div className={styles.library_filterbar_row1}>
            {/* Search Box */}
            <div className={styles.library_search_box}>
              <svg
                className={styles.library_search_icon}
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                id="library_search"
                className={styles.library_search_input}
                placeholder="Search tours..."
                aria-label="Search tours"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setPage(1);
                  updateUrl("q", e.target.value, true);
                }}
              />
              <button
                type="button"
                className={`${styles.library_search_clear} ${query ? styles.visible : ""}`}
                id="library_search_clear"
                aria-label="Clear search"
                onClick={() => {
                  setQuery("");
                  setPage(1);
                  updateUrl("q", "", true);
                }}
              >
                ×
              </button>
            </div>

            {/* Controls: Sort, Categories, Language, Clear */}
            <div className={styles.library_filterbar_controls}>
              {/* Sort Toggle Pill */}
              <button
                type="button"
                className={styles.library_filter_pill}
                id="library_sort_toggle"
                aria-label={`Sort by publish date, currently ${order === "newest" ? "newest" : "oldest"} first. Activate to toggle sort order.`}
                onClick={() => {
                  const nextOrder = order === "newest" ? "oldest" : "newest";
                  setOrder(nextOrder);
                  setPage(1);
                  updateUrl("order", nextOrder === "newest" ? "" : nextOrder);
                }}
              >
                <span className={styles.library_filter_pill_label}>
                  Publish Date
                </span>
                <span className={styles.library_dropdown_value} id="library_sort_value">
                  {order === "newest" ? "Newest first" : "Oldest first"}
                </span>
              </button>

              {/* Categories / Region Dropdown */}
              <div
                className={styles.library_dropdown}
                ref={categoryDropdownRef}
                data-dropdown="categories"
              >
                <button
                  type="button"
                  className={`${styles.library_filter_pill} ${styles.library_dropdown_trigger}`}
                  id="library_category_trigger"
                  aria-haspopup="listbox"
                  aria-expanded={openDropdown === "category"}
                  aria-controls="library_category_menu"
                  onClick={() =>
                    setOpenDropdown(openDropdown === "category" ? null : "category")
                  }
                >
                  <span className={styles.library_filter_pill_label}>
                    Categories
                  </span>
                  <span className={styles.library_dropdown_value} id="library_category_value">
                    {region || "All"}
                  </span>
                  <span className={styles.library_dropdown_arrow}>▾</span>
                </button>
                {openDropdown === "category" && (
                  <div
                    className={styles.library_dropdown_menu}
                    role="listbox"
                    id="library_category_menu"
                  >
                    <button
                      type="button"
                      className={`${styles.library_dropdown_item} ${!region ? styles.active : ""}`}
                      role="option"
                      aria-selected={!region}
                      onClick={() => {
                        setRegion("");
                        setPage(1);
                        updateUrl("region", "");
                        setOpenDropdown(null);
                      }}
                    >
                      All categories
                    </button>
                    {categoryCounts.map(({ name, count }) => (
                      <button
                        key={name}
                        type="button"
                        className={`${styles.library_dropdown_item} ${region === name ? styles.active : ""}`}
                        role="option"
                        aria-selected={region === name}
                        onClick={() => {
                          setRegion(name);
                          setPage(1);
                          updateUrl("region", name);
                          setOpenDropdown(null);
                        }}
                      >
                        <span>{name}</span>
                        <span className={styles.tag_count}>({count})</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Language Dropdown */}
              <div
                className={styles.library_dropdown}
                ref={languageDropdownRef}
                data-dropdown="language"
              >
                <button
                  type="button"
                  className={`${styles.library_filter_pill} ${styles.library_dropdown_trigger}`}
                  id="library_language_trigger"
                  aria-haspopup="listbox"
                  aria-expanded={openDropdown === "language"}
                  aria-controls="library_language_menu"
                  onClick={() =>
                    setOpenDropdown(openDropdown === "language" ? null : "language")
                  }
                >
                  <span className={styles.library_filter_pill_label}>Language</span>
                  <span className={styles.library_dropdown_value} id="library_language_value">
                    {language || "All"}
                  </span>
                  <span className={styles.library_dropdown_arrow}>▾</span>
                </button>
                {openDropdown === "language" && (
                  <div
                    className={styles.library_dropdown_menu}
                    role="listbox"
                    id="library_language_menu"
                  >
                    <button
                      type="button"
                      className={`${styles.library_dropdown_item} ${!language ? styles.active : ""}`}
                      role="option"
                      aria-selected={!language}
                      onClick={() => {
                        setLanguage("");
                        setPage(1);
                        updateUrl("language", "");
                        setOpenDropdown(null);
                      }}
                    >
                      All languages
                    </button>
                    {languageCounts.map(({ name, count }) => (
                      <button
                        key={name}
                        type="button"
                        className={`${styles.library_dropdown_item} ${language === name ? styles.active : ""}`}
                        role="option"
                        aria-selected={language === name}
                        onClick={() => {
                          setLanguage(name);
                          setPage(1);
                          updateUrl("language", name);
                          setOpenDropdown(null);
                        }}
                      >
                        <span>{name}</span>
                        <span className={styles.tag_count}>({count})</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Clear All Filters */}
              <button
                type="button"
                id="library_clear_filters"
                className={`${styles.library_filter_pill} ${styles.library_clear_pill}`}
                disabled={!hasActiveFilters}
                onClick={handleClearAll}
              >
                Clear all
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Screen Reader Status */}
      <div className={styles.sr_only} role="status" id="library_results_status">
        {filtered.length} tours found
      </div>

      {/* 3. Card Group Grid */}
      <div
        className={styles.libraryCard_Group}
        id="libraryCard_Group"
        role="main"
        tabIndex={-1}
      >
        {status === "loading" && (
          <div className={styles.library_state} role="status">
            <p>Loading immersive heritage experiences…</p>
          </div>
        )}

        {status === "error" && (
          <div className={styles.library_state} role="alert">
            <p>Unable to load heritage tours.</p>
            <button
              type="button"
              className={styles.library_state_btn}
              onClick={() => setAttempt((val) => val + 1)}
            >
              Try again
            </button>
          </div>
        )}

        {status === "ready" && items.length === 0 && (
          <div className={styles.library_state}>
            <p>No heritage experiences available.</p>
          </div>
        )}

        {status === "ready" && items.length > 0 && filtered.length === 0 && (
          <div className={styles.library_no_results} role="status">
            <div className={styles.library_no_results_icon}>🔍</div>
            <p>No tours found matching your filters.</p>
            <button
              type="button"
              className={styles.library_no_results_clear}
              onClick={handleClearAll}
            >
              Clear all filters
            </button>
          </div>
        )}

        {status === "ready" &&
          visibleItems.map((item) => {
            const cardData: PortraitCardData = {
              slug: item.slug,
              title: item.title,
              description: item.description || item.tagline,
              region: item.region,
              card_image_url: item.card_image_url || item.splash_image_url,
              hover_video_url: item.hover_video_url,
              published: item.publish_date
                ? `Published ${(() => {
                    const d = new Date(item.publish_date);
                    return isNaN(d.getFullYear())
                      ? item.publish_date
                      : d.getFullYear();
                  })()}`
                : "Published 2026",
              language_label:
                [item.language1?.name, item.language2?.name]
                  .filter(Boolean)
                  .join(", ") || "English",
              community_made: Boolean(item.community_made),
              href: `/content/${encodeURIComponent(item.slug)}`,
            };

            return (
              <PortraitCard
                key={item.slug}
                className={styles.libraryCard}
                variant="default"
                item={cardData}
                onInfo={(slug) => {
                  router.push(`/content/${encodeURIComponent(slug)}`);
                }}
              />
            );
          })}
      </div>

      {/* 4. Pagination */}
      {status === "ready" && totalPages > 1 && (
        <div className={styles.library_pagination_wrapper}>
          <Pagination
            page={currentPage}
            totalPages={totalPages}
            onPageChange={(value) => {
              setPage(value);
              updateUrl("page", value === 1 ? "" : String(value));
            }}
          />
        </div>
      )}
    </div>
  );
}
