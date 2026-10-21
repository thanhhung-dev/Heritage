"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useParams, usePathname, useRouter } from "next/navigation";

import { HeritageTourProvider } from "@/context/heritage-tour";
import HeritageViewer from "@/features/tour/HeritageViewer";
import HeritageCanvas from "@/features/tour/three/HeritageCanvas";
import type { TourEngine } from "@/features/tour/three/tour-engine";
import { DEMO_HERITAGE_PAYLOAD } from "@/lib/demo-heritage";
import { fetchHeritagePayload } from "@/lib/heritage";
import { isInteractivePath } from "@/lib/tour-routes";
import type { HeritagePayload } from "@/types/heritage";
import { TEST_TOUR } from "@/features/tour/tour-data";
import styles from "./content-shell.module.css";

type TourState = {
  payload: HeritagePayload;
  status: "ready";
  error: string | null;
} | {
  payload: HeritagePayload;
  status: "demo";
  error: string | null;
};

/**
 * Fullscreen 3D tour layout (`/content/{slug}/...`).
 *
 * Rendering is IMMEDIATE: the demo payload is shown right away so the UI team
 * can develop the interface without the backend. The real full single-load
 * payload is fetched in the background and replaces the demo when it arrives.
 * Navigating between `/s0..sN` never refetches.
 */
export default function HeritageContentLayout({
  children,
}: {
  children: ReactNode;
}) {
  const params = useParams<{ slug: string; sceneKey?: string }>();
  const router = useRouter();
  const pathname = usePathname();
  const slug = params.slug;
  // `/content/{slug}/{sceneKey}/int` ⇒ đang ở chế độ điểm tương tác. Layout là nơi
  // biết URL, nên nó quyết định; `HeritageViewer` và `useTourPlayer` chỉ tiêu thụ
  // cờ này, không tự đoán lại từ pathname.
  const interactiveRoute = isInteractivePath(pathname);
  const fixture = slug === "tapestry-test" ? TEST_TOUR : null;
  const [engine, setEngine] = useState<TourEngine | null>(null);
  const [modelError, setModelError] = useState<string | null>(null);
  const isModelReady = engine !== null;

  useEffect(() => {
    if (params.sceneKey && !isModelReady) {
      router.replace(`/content/${slug}`);
    }
  }, [params.sceneKey, isModelReady, router, slug]);

  const [state, setState] = useState<TourState>({
    payload: fixture?.payload ?? DEMO_HERITAGE_PAYLOAD,
    status: fixture ? "ready" : "demo",
    error: null,
  });

  useEffect(() => {
    if (fixture) return;
    let cancelled = false;

    fetchHeritagePayload(slug)
      .then((payload) => {
        if (cancelled) return;
        // Only use the real payload when it actually has scenes to show.
        // Otherwise keep the embedded demo so the UI is always visible.
        const hasContent = !!payload && (!!payload.overview || payload.scenes.length > 0);
        setState(
          hasContent
            ? { payload, status: "ready", error: null }
            : { payload: DEMO_HERITAGE_PAYLOAD, status: "demo", error: null }
        );
      })
      .catch((err) => {
        if (!cancelled) {
          setState((prev) => ({
            ...prev,
            error:
              err instanceof Error
                ? err.message
                : "Không thể tải dữ liệu từ backend. Đang hiển thị dữ liệu demo.",
          }));
        }
      });

    return () => {
      cancelled = true;
    };
  }, [slug, fixture]);

  return (
    <div className={styles.shell}>
      <HeritageTourProvider
        payload={fixture?.payload ?? state.payload}
        heritageSlug={slug}
        currentSceneKey={params.sceneKey ?? "s0"}
        status={fixture ? "ready" : state.status}
        error={fixture ? null : state.error}
        engine={engine}
        modelError={modelError}
        playback={fixture?.playback}
      >
        <HeritageCanvas
          onReady={setEngine}
          onError={setModelError}
          modelUrl={fixture?.modelUrl}
        />
        {params.sceneKey && isModelReady ? <HeritageViewer interactiveRoute={interactiveRoute} /> : null}
        {children}
      </HeritageTourProvider>
    </div>
  );
}
