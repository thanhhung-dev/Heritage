"use client";

import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { HeritageTourProvider } from "@/context/heritage-tour";
import { DEMO_HERITAGE_PAYLOAD } from "@/lib/demo-heritage";
import { fetchHeritagePayload } from "@/lib/heritage";
import type { HeritagePayload } from "@/types/heritage";
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
  const params = useParams<{ slug: string }>();
  const slug = params.slug;

  const [state, setState] = useState<TourState>({
    payload: DEMO_HERITAGE_PAYLOAD,
    status: "demo",
    error: null,
  });

  useEffect(() => {
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
  }, [slug]);

  return (
    <div className={styles.shell}>
      <HeritageTourProvider
        payload={state.payload}
        heritageSlug={slug}
        initialSceneKey="s0"
        status={state.status}
        error={state.error}
      >
        {children}
      </HeritageTourProvider>
    </div>
  );
}