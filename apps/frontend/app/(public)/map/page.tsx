import Script from "next/script";
import { apiClient } from "@/config/api";
import { PUBLIC_ROUTE_BY_KEY } from "@/config/public-navigation";
import type { HeritageSummary } from "@/types/heritage";
import styles from "./map.module.css";

const route = PUBLIC_ROUTE_BY_KEY.map;
const MAPTILER_SDK_VERSION = "v4.2.0";

function hasValidCoordinates(
  heritage: HeritageSummary,
): heritage is HeritageSummary & { lat: number; lng: number } {
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

function serializeForScript(value: unknown): string {
  return JSON.stringify(value)
    .replace(/</g, "\\u003c")
    .replace(/\u2028/g, "\\u2028")
    .replace(/\u2029/g, "\\u2029");
}

export const metadata = {
  title: route.title,
  description: route.description,
  alternates: { canonical: route.href },
};

export default async function MapPage() {
  const apiKey = process.env.NEXT_PUBLIC_MAPTILER_API_KEY?.trim() ?? "";
  let heritages: HeritageSummary[] = [];
  let locationsError = false;

  try {
    heritages = await apiClient<HeritageSummary[]>("/heritages", {
      cache: "no-store",
    });
  } catch (error) {
    console.error("Could not load heritage map locations.", error);
    locationsError = true;
  }

  const locations = (Array.isArray(heritages) ? heritages : [])
    .filter(hasValidCoordinates)
    .map(({ id, title, lat, lng }) => ({ id, title, lat, lng }));

  const mapInitScript = apiKey
    ? [
        "(function () {",
        '  const container = document.getElementById("heritage-map-canvas");',
        '  const status = document.getElementById("heritage-map-loading");',
        '  if (!container || container.dataset.mapInitialized === "true") return;',
        '  container.dataset.mapInitialized = "true";',
        "  const apiKey = " + serializeForScript(apiKey) + ";",
        "  const locations = " + serializeForScript(locations) + ";",
        '  const sdkBase = "https://cdn.maptiler.com/maptiler-sdk-js/' +
          MAPTILER_SDK_VERSION +
          '/";',
        "  const showMapError = function () {",
        "    if (!status) return;",
        '    status.textContent = "Không thể tải bản đồ. Kiểm tra API key, quyền localhost và kết nối mạng.";',
        "    status.hidden = false;",
        "  };",
        '  const cssId = "heritage-maptiler-sdk-css";',
        "  if (!document.getElementById(cssId)) {",
        '    const link = document.createElement("link");',
        "    link.id = cssId;",
        '    link.rel = "stylesheet";',
        '    link.href = sdkBase + "maptiler-sdk.css";',
        "    document.head.appendChild(link);",
        "  }",
        "  const initializeMap = function () {",
        "    if (!container.isConnected || !window.maptilersdk) return;",
        "    const sdk = window.maptilersdk;",
        "    sdk.config.apiKey = apiKey;",
        "    const map = new sdk.Map({",
        "      container: container,",
        "      style: sdk.MapStyle.DATAVIZ.DARK,",
        "      center: [0, 20],",
        "      zoom: 1.5,",
        "      minZoom: 1,",
        "      attributionControl: true",
        "    });",
        '    map.addControl(new sdk.NavigationControl(), "top-right");',
        "    let styleLoaded = false;",
        '    map.on("load", function () {',
        "      styleLoaded = true;",
        "      if (status) status.hidden = true;",
        "    });",
        '    map.on("error", function (event) {',
        "      if (!styleLoaded) showMapError();",
        '      console.error("MapTiler map error.", event && event.error ? event.error : event);',
        "    });",
        "    locations.forEach(function (location) {",
        '      const markerElement = document.createElement("span");',
        "      markerElement.className = " + serializeForScript(styles.marker) + ";",
        "      markerElement.title = location.title;",
        '      markerElement.setAttribute("aria-label", location.title);',
        '      new sdk.Marker({ element: markerElement, anchor: "center" })',
        "        .setLngLat([location.lng, location.lat])",
        "        .setPopup(new sdk.Popup({ closeButton: true, offset: 12 }).setText(location.title))",
        "        .addTo(map);",
        "    });",
        "  };",
        "  if (window.maptilersdk) {",
        "    initializeMap();",
        "    return;",
        "  }",
        '  const sdkScript = document.createElement("script");',
        '  sdkScript.src = sdkBase + "maptiler-sdk.umd.min.js";',
        "  sdkScript.async = true;",
        "  sdkScript.onload = initializeMap;",
        "  sdkScript.onerror = showMapError;",
        "  document.head.appendChild(sdkScript);",
        "})();",
      ].join("\n")
    : "";

  return (
    <section className={styles.mapPage} aria-label={route.title}>
      <h1 className={styles.visuallyHidden}>{route.title}</h1>
      <div
        className={styles.mapFrame}
        role="region"
        aria-label={"Bản đồ MapTiler với " + locations.length + " địa điểm di sản"}
      >
        <div id="heritage-map-canvas" className={styles.mapCanvas} />
        {apiKey ? (
          <div
            id="heritage-map-loading"
            className={styles.mapStatus}
            role="status"
            aria-live="polite"
          >
            Đang tải bản đồ…
          </div>
        ) : (
          <div className={styles.setupNotice} role="alert">
            <strong>Chưa cấu hình MapTiler API key</strong>
            <span>
              Thêm NEXT_PUBLIC_MAPTILER_API_KEY vào apps/frontend/.env.local
            </span>
          </div>
        )}
        {apiKey && (locationsError || locations.length === 0) && (
          <div
            className={styles.dataNotice}
            role={locationsError ? "alert" : "status"}
          >
            {locationsError
              ? "Không tải được danh sách địa điểm di sản. Bản đồ vẫn có thể sử dụng."
              : "Chưa có địa điểm di sản với tọa độ hợp lệ để hiển thị."}
          </div>
        )}
      </div>
      {apiKey && (
        <Script id="heritage-maptiler-init" strategy="afterInteractive">
          {mapInitScript}
        </Script>
      )}
    </section>
  );
}