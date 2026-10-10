"use client";

import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useMemo, useState } from "react";

import type { HeritagePayload, HeritageScene } from "@/types/heritage";
import { resolveSceneByKey } from "@/lib/heritage";

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
  setCurrentSceneKey: (key: string) => void;
  status: "demo" | "ready";
  error: string | null;
}

export const HeritageTourContext = createContext<HeritageTourContextValue | null>(
  null
);

interface HeritageTourProviderProps {
  payload: HeritagePayload;
  heritageSlug: string;
  initialSceneKey: string;
  status: "demo" | "ready";
  error: string | null;
  children: ReactNode;
}

export function HeritageTourProvider({
  payload,
  heritageSlug,
  initialSceneKey,
  status,
  error,
  children,
}: HeritageTourProviderProps) {
  const [currentSceneKey, setCurrentSceneKey] = useState<string>(initialSceneKey);

  const currentScene = useMemo(
    () => resolveSceneByKey(payload, currentSceneKey),
    [payload, currentSceneKey]
  );

  const handleSetSceneKey = useCallback((key: string) => {
    setCurrentSceneKey(key);
  }, []);

  const value = useMemo<HeritageTourContextValue>(
    () => ({
      payload,
      heritageSlug,
      currentSceneKey,
      currentScene,
      setCurrentSceneKey: handleSetSceneKey,
      status,
      error,
    }),
    [payload, heritageSlug, currentSceneKey, currentScene, handleSetSceneKey, status, error]
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