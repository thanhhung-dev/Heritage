"use client";

import type { ReactNode } from "react";
import { createContext, useContext, useMemo } from "react";

import type { HeritagePayload, HeritageScene } from "@/types/heritage";
import { resolveSceneByKey } from "@/lib/heritage";
import type { TourEngine } from "@/features/tour/three/tour-engine";

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
  status: "demo" | "ready";
  error: string | null;
  isModelReady: boolean;
  engine: TourEngine | null;
}

export const HeritageTourContext = createContext<HeritageTourContextValue | null>(
  null
);

interface HeritageTourProviderProps {
  payload: HeritagePayload;
  heritageSlug: string;
  currentSceneKey: string;
  status: "demo" | "ready";
  error: string | null;
  engine: TourEngine | null;
  children: ReactNode;
}

export function HeritageTourProvider({
  payload,
  heritageSlug,
  currentSceneKey,
  status,
  error,
  engine,
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
      status,
      error,
      isModelReady: engine !== null,
      engine,
    }),
    [payload, heritageSlug, currentSceneKey, currentScene, status, error, engine]
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
