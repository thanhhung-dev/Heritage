"use client";

import type { ReactNode } from "react";
import { createContext, useContext, useMemo } from "react";

import type { HeritagePayload, HeritageScene } from "@/types/heritage";
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
  playback,
  children,
}: HeritageTourProviderProps) {
  const currentScene = useMemo(
    () => resolveSceneByKey(payload, currentSceneKey),
    [payload, currentSceneKey]
  );

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
