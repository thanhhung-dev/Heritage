"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useRouter } from "next/navigation";
import { Button, ConfigProvider, theme } from "antd";
import { CloseOutlined, UnorderedListOutlined } from "@ant-design/icons";
import type { Map as MapLibreMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import PortraitCard from "@/components/PortraitCard/PortraitCard";
import { apiClient, ApiError } from "@/config/api";
import { PUBLIC_ROUTE_BY_KEY } from "@/config/public-navigation";
import type { HeritageSummary } from "@/types/heritage";
import styles from "@/app/(public)/map/map.module.css";

const route = PUBLIC_ROUTE_BY_KEY.map;
const MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
type MapLibrary = typeof import("maplibre-gl");
type LocatedHeritage = HeritageSummary & { lat: number; lng: number };

function hasValidCoordinates(
  heritage: HeritageSummary,
): heritage is LocatedHeritage {
  return (
    typeof heritage.lat === "number" &&
    Number.isFinite(heritage.lat) &&
    heritage.lat >= -90 &&
    heritage.lat <= 90 &&
    typeof heritage.lng === "number" &&
    Number.isFinite(heritage.lng) &&
    heritage.lng >= -180 &&
    heritage.lng <= 180
  );
}

function fitLocations(map: MapLibreMap, locations: LocatedHeritage[], animate = true) {
  if (!locations.length) return;
  const lngs = locations.map((place) => place.lng);
  const lats = locations.map((place) => place.lat);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  map.fitBounds(
    [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
    {
      padding: Math.max(32, Math.min(72, map.getContainer().clientWidth * 0.1)),
      maxZoom: 14,
      duration: animate && !reducedMotion ? 500 : 0,
    },
  );
}

function PlaceMarker({
  map,
  library,
  place,
  selected,
  onSelect,
}: {
  map: MapLibreMap;
  library: MapLibrary;
  place: LocatedHeritage;
  selected: boolean;
  onSelect: (slug: string, trigger: HTMLButtonElement) => void;
}) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);
  const [highlighted, setHighlighted] = useState(false);

  useEffect(() => {
    const element = document.createElement("div");
    element.className = styles.markerAnchor;
    const marker = new library.Marker({ element, anchor: "center" })
      .setLngLat([place.lng, place.lat])
      .addTo(map);
    setContainer(element);
    return () => { marker.remove(); };
  }, [map, library, place.lng, place.lat]);

  useEffect(() => {
    if (container) container.style.zIndex = highlighted ? "3" : selected ? "2" : "1";
  }, [container, highlighted, selected]);

  return container ? createPortal(
    <button
      type="button"
      className={styles.markerVisual}
      data-heritage-marker={place.slug}
      data-selected={selected}
      data-highlighted={highlighted}
      aria-label={`Xem thông tin ${place.title}`}
      aria-pressed={selected}
      aria-controls={selected ? "heritage-selected-card" : undefined}
      onPointerEnter={() => setHighlighted(true)}
      onPointerLeave={() => setHighlighted(false)}
      onFocus={() => setHighlighted(true)}
      onBlur={() => setHighlighted(false)}
      onClick={(event) => {
        event.stopPropagation();
        onSelect(place.slug, event.currentTarget);
      }}
    >
      <span className={styles.markerPulse} aria-hidden="true" />
      <span className={styles.markerRing} aria-hidden="true" />
      <span className={styles.markerGlow} aria-hidden="true" />
      <span className={styles.markerCore} aria-hidden="true" />
      {highlighted || selected ? (
        <span className={styles.markerLabel} aria-hidden="true">
          <span className={styles.markerName}>{place.title}</span>
        </span>
      ) : null}
    </button>,
    container,
  ) : null;
}

export default function MapPage() {
  const router = useRouter();
  const canvas = useRef<HTMLDivElement | null>(null);
  const selectionTrigger = useRef<HTMLButtonElement | null>(null);
  const [map, setMap] = useState<MapLibreMap | null>(null);
  const [library, setLibrary] = useState<MapLibrary | null>(null);
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
        if (!Array.isArray(response)) throw new Error("Invalid heritage response");
        if (!controller.signal.aborted) setHeritages(response);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setLocationsError(error instanceof ApiError
          ? `Máy chủ dữ liệu trả lỗi HTTP ${error.status}. Vui lòng thử lại.`
          : "Không kết nối được máy chủ dữ liệu. Vui lòng thử lại.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLocationsLoading(false);
      });
    return () => controller.abort();
  }, [requestVersion]);

  useEffect(() => {
    if (!canvas.current) return;
    let cancelled = false;
    let instance: MapLibreMap | undefined;
    let observer: ResizeObserver | undefined;
    setMap(null);
    setMapReady(false);
    setMapError(null);
    const timeout = window.setTimeout(() => {
      if (!cancelled) setMapError("Bản đồ tải chậm. Kiểm tra kết nối mạng hoặc thử lại.");
    }, 20000);

    import("maplibre-gl").then((lib) => {
      if (cancelled || !canvas.current) return;
      // MapLibre 6 ships a separate module worker. Pin it to the installed version.
      lib.setWorkerUrl(
        `https://unpkg.com/maplibre-gl@${lib.getVersion()}/dist/maplibre-gl-worker.mjs`,
      );
      instance = new lib.Map({
        container: canvas.current,
        style: MAP_STYLE,
        center: [108, 16.2],
        zoom: 8,
        minZoom: 2,
        maxZoom: 18,
        renderWorldCopies: false,
        attributionControl: { compact: true },
      });
      const currentMap = instance;
      const ready = () => {
        if (cancelled) return;
        window.clearTimeout(timeout);
        setMapReady(true);
        setMapError(null);
      };
      currentMap.on("load", ready);
      currentMap.on("idle", () => {
        if (currentMap.isStyleLoaded()) ready();
      });
      currentMap.on("error", () => {
        if (!currentMap.getStyle()) {
          setMapError("Không tải được nền bản đồ. Vui lòng thử lại.");
        }
      });
      currentMap.on("click", (event) => {
        const target = event.originalEvent.target;
        if (!(target instanceof Element) || !target.closest("[data-heritage-marker]")) {
          setSelectedSlug(null);
        }
      });
      observer = new ResizeObserver(() => currentMap.resize());
      observer.observe(canvas.current);
      setLibrary(lib);
      setMap(currentMap);
    }).catch(() => {
      if (!cancelled) {
        window.clearTimeout(timeout);
        setMapError("Không khởi tạo được bản đồ. Hãy kiểm tra WebGL và kết nối mạng.");
      }
    });

    return () => {
      cancelled = true;
      window.clearTimeout(timeout);
      observer?.disconnect();
      instance?.remove();
    };
  }, [mapAttempt]);

  const locations = useMemo(
    () => heritages.filter(hasValidCoordinates).filter((place) => place.display_map !== false),
    [heritages],
  );
  const regionCount = new Set(locations.map((place) => place.region).filter(Boolean)).size;
  const selectedPlace = locations.find((place) => place.slug === selectedSlug);
  const statsPending = locationsLoading || Boolean(locationsError);

  useEffect(() => {
    if (map) fitLocations(map, locations, false);
  }, [map, locations]);

  const closeCard = () => {
    setSelectedSlug(null);
    if (selectionTrigger.current?.isConnected) selectionTrigger.current.focus();
  };

  return (
    <ConfigProvider theme={{
      algorithm: theme.darkAlgorithm,
      token: {
        colorPrimary: "#ff9b2d", colorBgContainer: "#22201d",
        colorText: "#f0f2f3", borderRadius: 10, fontFamily: "Poppins, Arial, sans-serif",
      },
    }}>
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
        <h1 className={styles.visuallyHidden}>{route.title}</h1>
        <div className={styles.mapExperience}>
          <aside className={styles.mapAside} aria-label="Thông tin di sản đang chọn">
            {selectedPlace ? (
              <div key={selectedPlace.slug} id="heritage-selected-card" className={styles.selectedCard}>
                <Button
                  className={styles.closeCard}
                  type="text"
                  shape="circle"
                  icon={<CloseOutlined />}
                  aria-label={`Đóng thẻ ${selectedPlace.title}`}
                  onClick={closeCard}
                />
                <PortraitCard
                  item={{
                    slug: selectedPlace.slug,
                    title: selectedPlace.title,
                    description: selectedPlace.description,
                    region: selectedPlace.region,
                    card_image_url: selectedPlace.card_image_url || selectedPlace.splash_image_url,
                    hover_image_url: selectedPlace.splash_image_url,
                    published: selectedPlace.publish_date,
                    language_label: selectedPlace.language1?.name,
                    href: `/content/${encodeURIComponent(selectedPlace.slug)}/s0`,
                  }}
                  style={{ width: "100%", height: "auto", aspectRatio: "2 / 3", borderRadius: 18 }}
                  onInfo={(slug) => router.push(`/content/${encodeURIComponent(slug)}`)}
                  exploreLabel="Khám phá"
                  infoLabel="Thông tin"
                />
              </div>
            ) : null}
            <div className={styles.exploreSummary}>
              <dl className={styles.mapStats}>
                <div className={styles.stat}>
                  <dt>ĐỊA ĐIỂM</dt>
                  <dd>{statsPending ? "—" : locations.length}</dd>
                </div>
                <div className={styles.stat}>
                  <dt>KHU VỰC</dt>
                  <dd>{statsPending ? "—" : regionCount}</dd>
                </div>
              </dl>
              <p className={styles.mapDescription}>Khám phá những câu chuyện di sản</p>
              <a className={styles.listLink} href={PUBLIC_ROUTE_BY_KEY.library.href}>
                <UnorderedListOutlined aria-hidden="true" />
                <span>Duyệt danh sách địa điểm</span>
              </a>
            </div>
            <div className={styles.statusArea}>
              {locationsLoading ? (
                <p role="status" className={styles.inlineStatus}>Đang tải địa điểm…</p>
              ) : locationsError ? (
                <div role="alert" className={styles.inlineStatus}>
                  <p>{locationsError}</p>
                  <Button size="small" onClick={() => setRequestVersion((value) => value + 1)}>
                    Thử lại
                  </Button>
                </div>
              ) : !locations.length ? (
                <p role="status" className={styles.inlineStatus}>
                  Chưa có địa điểm với tọa độ hợp lệ.
                </p>
              ) : null}
            </div>
            <p className={styles.visuallyHidden} role="status" aria-live="polite">
              {selectedPlace ? `Đã mở thẻ ${selectedPlace.title}, ${selectedPlace.region ?? ""}.` : ""}
            </p>
          </aside>
          <div className={styles.mapFrame} role="region" aria-label={`Bản đồ với ${locations.length} địa điểm di sản`}>
            <div ref={canvas} className={styles.mapCanvas} />
            {map && library ? locations.map((place) => (
              <PlaceMarker
                key={place.id}
                map={map}
                library={library}
                place={place}
                selected={selectedSlug === place.slug}
                onSelect={(slug, trigger) => {
                  selectionTrigger.current = trigger;
                  setSelectedSlug(slug);
                }}
              />
            )) : null}
            {!mapReady || mapError ? (
              <div className={styles.mapNotice} role={mapError ? "alert" : "status"}>
                <span>{mapError || "Đang tải bản đồ…"}</span>
                {mapError ? (
                  <Button size="small" onClick={() => setMapAttempt((value) => value + 1)}>
                    Tải lại bản đồ
                  </Button>
                ) : null}
              </div>
            ) : null}
            <div className={styles.mapControls} role="group" aria-label="Điều khiển bản đồ">
              <Button aria-label="Phóng to bản đồ" disabled={!map} onClick={() => map?.zoomIn()}>+</Button>
              <Button aria-label="Thu nhỏ bản đồ" disabled={!map} onClick={() => map?.zoomOut()}>−</Button>
              <Button disabled={!map || !locations.length} onClick={() => {
                if (map) fitLocations(map, locations);
              }}>Tất cả địa điểm</Button>
            </div>
          </div>
        </div>
      </section>
    </ConfigProvider>
  );
}
