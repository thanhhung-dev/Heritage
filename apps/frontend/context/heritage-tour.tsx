"use client";

import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import type { HeritageInteractiveHighlight, HeritagePayload, HeritageScene } from "@/types/heritage";
import type { NarrationStatus, TourMode } from "@/features/chat/types";
import { resolveSceneByKey } from "@/lib/heritage";
import type { TourEngine } from "@/features/tour/three/tour-engine";
import type { ScenePlayback } from "@/features/tour/tour-data";

/**
 * React context that holds the full single-load heritage payload for the
 * current tour. Fetched ONCE in `app/(public)/content/[slug]/tour/layout.tsx`
 * and shared across every `/s0..sN` route — scene switches never refetch.
 */
export interface HeritageTourContextValue {
  payload: HeritagePayload;
  heritageSlug: string;
  currentSceneKey: string;
  currentScene: HeritageScene | null;
  error: string | null;
  isModelReady: boolean;
  modelError: string | null;
  /** 0..1 — tiến độ tải GLB. `0` khi tour không có model hoặc chưa bắt đầu. */
  modelProgress: number;
  /** Tour này có model 3D để tải hay không (`modelUrl` khác null). */
  hasModel: boolean;
  engine: TourEngine | null;
  scenePlayback: ScenePlayback | null;
  selectedHighlight: HeritageInteractiveHighlight | null;
  setSelectedHighlight: (point: HeritageInteractiveHighlight | null) => void;
  chatMode: TourMode;
  narrationStatus: NarrationStatus;
  reportNarration: (sceneKey: string, status: NarrationStatus) => void;
}

export const HeritageTourContext = createContext<HeritageTourContextValue | null>(
  null
);

interface HeritageTourProviderProps {
  payload: HeritagePayload;
  heritageSlug: string;
  currentSceneKey: string;
  error: string | null;
  engine: TourEngine | null;
  modelError: string | null;
  modelProgress?: number;
  hasModel?: boolean;
  interactiveRoute?: boolean;
  playback?: Record<string, ScenePlayback>;
  children: ReactNode;
}

export function HeritageTourProvider({
  payload,
  heritageSlug,
  currentSceneKey,
  error,
  engine,
  modelError,
  modelProgress = 0,
  hasModel = false,
  interactiveRoute = false,
  playback,
  children,
}: HeritageTourProviderProps) {
  const currentScene = useMemo(
    () => resolveSceneByKey(payload, currentSceneKey),
    [payload, currentSceneKey]
  );
  const [selection, setSelection] = useState<{ key: string; id: number } | null>(null);
  const setSelectedHighlight = useCallback((point: HeritageInteractiveHighlight | null) => {
    setSelection(point ? { key: currentSceneKey, id: point.id } : null);
  }, [currentSceneKey]);
  const interactive = playback?.[currentSceneKey] ? currentScene?.interactive[0] : null;
  const chatMode: TourMode = !interactiveRoute || !interactive ? "scene"
    : interactive.mode === "free_explore" ? "walk" : interactive.mode === "free" ? "free" : "standard";
  useEffect(() => { setSelection(null); }, [currentSceneKey, chatMode]);
  const selectedHighlight = chatMode !== "scene" && selection?.key === currentSceneKey
    ? interactive?.highlights.find((point) => point.id === selection.id) ?? null : null;
  const [narration, setNarration] = useState<Record<string, NarrationStatus>>({});
  const reportNarration = useCallback((key: string, status: NarrationStatus) => {
    setNarration((previous) => previous[key] === status ? previous
      : Object.fromEntries([...Object.entries(previous).filter(([entry]) => entry !== key), [key, status]].slice(-32)));
  }, []);
  const narrationStatus = narration[currentSceneKey]
    ?? (playback?.[currentSceneKey]?.narrationUrl ? "not_started" : "unavailable");

  const value = useMemo<HeritageTourContextValue>(
    () => ({
      payload,
      heritageSlug,
      currentSceneKey,
      currentScene,
      error,
      isModelReady: engine !== null,
      modelError,
      modelProgress,
      hasModel,
      engine,
      scenePlayback: playback?.[currentSceneKey] ?? null,
      selectedHighlight, setSelectedHighlight, chatMode, narrationStatus, reportNarration,
    }),
    [
      payload,
      heritageSlug,
      currentSceneKey,
      currentScene,
      error,
      engine,
      modelError,
      modelProgress,
      hasModel,
      playback,
      selectedHighlight, setSelectedHighlight, chatMode, narrationStatus, reportNarration,
    ]
  );

  return (
    <HeritageTourContext.Provider value={value}>
      {children}
    </HeritageTourContext.Provider>
  );
}

export function useHeritageTour(): HeritageTourContextValue {
  const ctx = useContext(HeritageTourContext);
  if (!ctx) {
    throw new Error("useHeritageTour must be used within a <HeritageTourProvider>");
  }
  return ctx;
}
