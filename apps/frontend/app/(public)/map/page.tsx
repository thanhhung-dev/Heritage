"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";
import { CloseOutlined, UnorderedListOutlined } from "@ant-design/icons";
import type { MapHandle } from "@/features/map/HeritageMap";
import {
  parseBoundaries,
  parseDistricts,
  REGION_NAMES,
  visibleHeritages,
  type BoundaryCollection,
  type DistrictCollection,
} from "@/features/map/geography";
import PortraitCard from "@/components/PortraitCard/PortraitCard";
import { apiClient, ApiError } from "@/config/api";
import { PUBLIC_ROUTE_BY_KEY } from "@/config/public-navigation";
import type { HeritageSummary } from "@/types/heritage";
import styles from "@/app/(public)/map/map.module.css";

const route = PUBLIC_ROUTE_BY_KEY.map;
const HeritageMap = dynamic(() => import("@/features/map/HeritageMap"), {
  ssr: false,
});

export default function MapPage() {
  const router = useRouter();
  const map = useRef<MapHandle>(null);
  const selectionTrigger = useRef<HTMLButtonElement | null>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const [boundaries, setBoundaries] = useState<BoundaryCollection | null>(null);
  const [districts, setDistricts] = useState<DistrictCollection | null>(null);
  const [mapAttempt, setMapAttempt] = useState(0);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);
  const [heritages, setHeritages] = useState<HeritageSummary[]>([]);
  const [locationsLoading, setLocationsLoading] = useState(true);
  const [requestVersion, setRequestVersion] = useState(0);
  const [locationsError, setLocationsError] = useState<string | null>(null);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);

  useEffect(() => {
    document.title = `${route.title} | Heritage`;
    const controller = new AbortController();
    setLocationsLoading(true);
    setLocationsError(null);
    apiClient<HeritageSummary[]>("/heritages", {
      cache: "no-store",
      signal: controller.signal,
    })
      .then((response) => {
        if (!Array.isArray(response))
          throw new Error("Invalid heritage response");
        if (!controller.signal.aborted) setHeritages(response);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setLocationsError(
          error instanceof ApiError
            ? `Máy chủ dữ liệu trả lỗi HTTP ${error.status}. Vui lòng thử lại.`
            : "Không kết nối được máy chủ dữ liệu. Vui lòng thử lại.",
        );
      })
      .finally(() => {
        if (!controller.signal.aborted) setLocationsLoading(false);
      });
    return () => controller.abort();
  }, [requestVersion]);

  useEffect(() => {
    const controller = new AbortController();
    setBoundaries(null);
    setDistricts(null);
    setMapReady(false);
    setMapError(null);
    fetch("/map/hue-da-nang.geojson", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error("Không tải được ranh giới bản đồ.");
        return parseBoundaries(await response.json());
      })
      .then((data) => {
        if (!controller.signal.aborted) setBoundaries(data);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted)
          setMapError(
            error instanceof Error ? error.message : "Không tải được bản đồ.",
          );
      });
    fetch("/map/hue-da-nang-districts.geojson", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) return null;
        return parseDistricts(await response.json());
      })
      .then((data) => {
        if (!controller.signal.aborted && data) setDistricts(data);
      })
      .catch(() => {
        // Optional sub-region overlay; keep main 3D map functional if it fails.
      });
    return () => controller.abort();
  }, [mapAttempt]);

  const locations = useMemo(
    () => (boundaries ? visibleHeritages(heritages, boundaries) : []),
    [heritages, boundaries],
  );
  const selectedPlace = locations.find((place) => place.slug === selectedSlug);
  const statsPending =
    locationsLoading || Boolean(locationsError) || !boundaries;

  useEffect(() => {
    if (mapReady || mapError) return;
    const timer = window.setTimeout(
      () => setMapError("Bản đồ tải chậm. Kiểm tra kết nối và thử lại."),
      20000,
    );
    return () => window.clearTimeout(timer);
  }, [mapReady, mapError, mapAttempt]);

  useEffect(() => {
    if (!selectedPlace) return;
    closeButton.current?.focus({ preventScroll: true });
    if (window.matchMedia("(max-width: 760px)").matches) {
      document.getElementById("heritage-selected-card")?.scrollIntoView({
        block: "center",
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? "auto"
          : "smooth",
      });
    }
  }, [selectedPlace]);

  const selectPlace = (slug: string, trigger: HTMLButtonElement) => {
    selectionTrigger.current = trigger;
    setSelectedSlug(slug);
    const place = locations.find((location) => location.slug === slug);
    if (place) map.current?.focus([place.lng, place.lat]);
  };

  const closeCard = () => {
    setSelectedSlug(null);
    map.current?.resetView();
    const list = selectionTrigger.current?.closest("details");
    if (list && !list.open) {
      list.querySelector("summary")?.focus();
    } else {
      selectionTrigger.current?.focus();
    }
  };
  const handleMapBackgroundClick = () => {
    setSelectedSlug(null);
    map.current?.resetView();
  };
  useEffect(() => {
    if (!selectedSlug) return;
    const onDocumentPointerDown = (event: PointerEvent) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (
        target.closest("#heritage-selected-card") ||
        target.closest("[data-heritage-marker]") ||
        target.closest(`.${styles.siteList}`)
      ) {
        return;
      }
      closeCard();
    };
    document.addEventListener("pointerdown", onDocumentPointerDown);
    return () => document.removeEventListener("pointerdown", onDocumentPointerDown);
  }, [selectedSlug]);

  return (
    <section
      className={styles.mapPage}
      aria-label={route.title}
      onKeyDown={(event) => {
        if (event.key === "Escape" && selectedSlug) {
          event.stopPropagation();
          closeCard();
        }
      }}
    >
      <h1 className={styles.visuallyHidden}>
        Khám phá di sản Huế và Đà Nẵng trên bản đồ 3D
      </h1>
      <div className={styles.mapExperience}>
        <aside className={styles.mapAside} aria-label="Khám phá di sản">
          {selectedPlace ? (
            <div
              key={selectedPlace.slug}
              id="heritage-selected-card"
              className={styles.selectedCard}
            >
              <button
                ref={closeButton}
                className={styles.closeCard}
                type="button"
                aria-label={`Đóng thẻ ${selectedPlace.title}`}
                onClick={closeCard}
              >
                <CloseOutlined />
              </button>
              <PortraitCard
                item={{
                  slug: selectedPlace.slug,
                  title: selectedPlace.title,
                  description: selectedPlace.description,
                  region: REGION_NAMES[selectedPlace.mapRegion],
                  card_image_url:
                    selectedPlace.card_image_url ||
                    selectedPlace.splash_image_url,
                  hover_image_url: selectedPlace.splash_image_url,
                  published: selectedPlace.publish_date,
                  language_label: selectedPlace.language1?.name,
                  href: `/content/${encodeURIComponent(selectedPlace.slug)}/s0`,
                }}
                style={{
                  width: "100%",
                  height: "auto",
                  aspectRatio: "2 / 3",
                  borderRadius: 14,
                }}
                onInfo={(slug) =>
                  router.push(`/content/${encodeURIComponent(slug)}`)
                }
                exploreLabel="Khám phá"
                infoLabel="Thông tin"
              />
            </div>
          ) : null}
          <div className={styles.exploreSummary}>
            <p className={styles.eyebrow}>HUẾ & ĐÀ NẴNG</p>
            <dl className={styles.mapStats}>
              <div className={styles.stat}>
                <dt>Địa điểm di sản</dt>
                <dd>{statsPending ? "—" : locations.length}</dd>
              </div>
              <div className={styles.stat}>
                <dt>Khu vực</dt>
                <dd>{boundaries ? "02" : "—"}</dd>
              </div>
            </dl>
            <p className={styles.mapDescription}>Khám phá di sản miền Trung</p>
            <p className={styles.regionNote}>
              Ranh giới mới · Đà Nẵng gồm Quảng Nam cũ
            </p>
          </div>
          <details className={styles.siteList}>
            <summary>
              <UnorderedListOutlined aria-hidden="true" />
              Duyệt danh sách di sản
            </summary>
            <nav aria-label="Danh sách di sản Huế và Đà Nẵng">
              <ul>
                {locations.map((place) => (
                  <li key={place.slug}>
                    <button
                      type="button"
                      aria-pressed={selectedPlace?.slug === place.slug}
                      aria-controls={
                        selectedPlace?.slug === place.slug
                          ? "heritage-selected-card"
                          : undefined
                      }
                      onClick={(event) =>
                        selectPlace(place.slug, event.currentTarget)
                      }
                    >
                      <span>{place.title}</span>
                      <span className={styles.listRegion}>
                        {REGION_NAMES[place.mapRegion]}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              {!locations.length ? (
                <p className={styles.listEmpty}>
                  Chưa có địa điểm để hiển thị.
                </p>
              ) : null}
            </nav>
          </details>
          <div className={styles.statusArea}>
            {locationsLoading ? (
              <p role="status" className={styles.inlineStatus}>
                Đang tải địa điểm…
              </p>
            ) : locationsError ? (
              <div role="alert" className={styles.inlineStatus}>
                <p>{locationsError}</p>
                <button
                  className={styles.retryButton}
                  type="button"
                  onClick={() => setRequestVersion((value) => value + 1)}
                >
                  Thử lại
                </button>
              </div>
            ) : boundaries && !locations.length ? (
              <p role="status" className={styles.inlineStatus}>
                Chưa có di sản được hiển thị với tọa độ hợp lệ trong Huế–Đà
                Nẵng.
              </p>
            ) : null}
          </div>
          <p className={styles.visuallyHidden} role="status" aria-live="polite">
            {selectedPlace
              ? `Đã mở thẻ ${selectedPlace.title}, ${REGION_NAMES[selectedPlace.mapRegion]}.`
              : ""}
          </p>
        </aside>
        <figure className={styles.mapFigure}>
          <div className={styles.mapFrame}>
            {boundaries && !mapError ? (
              <HeritageMap
                controlsRef={map}
                data={boundaries}
                districts={districts}
                locations={locations}
                selectedSlug={selectedPlace?.slug ?? null}
                onSelect={selectPlace}
                onBackgroundClick={handleMapBackgroundClick}
                onReady={() => {
                  setMapReady(true);
                  setMapError(null);
                }}
                onError={(message) => {
                  setMapReady(false);
                  setMapError(message);
                }}
              />
            ) : null}
            {!mapReady || mapError ? (
              <div
                className={styles.mapNotice}
                role={mapError ? "alert" : "status"}
              >
                <span>{mapError || "Loading…"}</span>
                {mapError ? (
                  <button
                    className={styles.retryButton}
                    type="button"
                    onClick={() => setMapAttempt((value) => value + 1)}
                  >
                    Tải lại bản đồ
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
        </figure>
      </div>
    </section>
  );
}
