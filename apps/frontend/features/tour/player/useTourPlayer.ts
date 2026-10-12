"use client";

import { useEffect, useRef, useState } from "react";
import { useHeritageTour } from "@/context/heritage-tour";
import type { HeritageInteractiveHighlight } from "@/types/heritage";
import type { ExploreMode } from "../three/explore-controller";
import type { TourEngine } from "../three/tour-engine";
import { useNarration } from "./useNarration";
import { useCaptions } from "./useCaptions";

export function useTourPlayer({ narrationUrl = null, captionsUrl = null }: {
  narrationUrl?: string | null;
  captionsUrl?: string | null;
} = {}) {
  const { engine, currentSceneKey, currentScene, scenePlayback } = useHeritageTour();
  const [isMuted, setIsMuted] = useState(false);
  const [ccOn, setCcOn] = useState(true);
  const [exploreMode, setExploreMode] = useState<ExploreMode | null>(null);
  const [selectedHighlight, setSelectedHighlight] = useState<HeritageInteractiveHighlight | null>(null);
  const [sceneError, setSceneError] = useState<string | null>(null);
  const [zoomed, setZoomed] = useState(false);
  const highlightEntry = useRef<ReturnType<TourEngine["getCameraPose"]> | null>(null);
  const narration = useNarration(narrationUrl ?? scenePlayback?.narrationUrl ?? null, isMuted);
  const captions = useCaptions(captionsUrl ?? scenePlayback?.captionsUrl ?? null, narration.currentTime, ccOn);
  const { pause, seek } = narration;

  useEffect(() => {
    pause();
    seek(0);
    engine?.exitExplore();
    let cancelled = false;
    setSceneError(null);
    if (scenePlayback && currentScene) engine?.applyCameraPreset(currentScene.camera);
    engine?.setInteractiveHighlights(scenePlayback ? currentScene?.interactive.flatMap((i) => i.highlights) ?? [] : []);
    void engine?.setSceneHighlights(scenePlayback?.timedHighlights ?? []).catch((error: unknown) => {
      if (!cancelled) setSceneError(error instanceof Error ? error.message : "Không tải được highlight.");
    });
    setExploreMode(null);
    setSelectedHighlight(null);
    setZoomed(false);
    highlightEntry.current = null;
    const unsubscribe = engine?.onHighlightSelect((item) => {
      setSelectedHighlight(item);
      if (item && scenePlayback && currentScene && item.cam_pos && item.cam_target) {
        highlightEntry.current ??= engine.getCameraPose();
        engine.applyCameraPreset({ ...currentScene.camera, start_position: item.cam_pos, start_target: item.cam_target });
      }
      if (!item) highlightEntry.current = null;
    });
    return () => { cancelled = true; unsubscribe?.(); };
  }, [engine, currentSceneKey, currentScene, scenePlayback, pause, seek]);
  useEffect(() => {
    engine?.setPlaybackTime(narration.currentTime);
  }, [engine, narration.currentTime]);

  function applyInteractiveCamera() {
    const interactive = scenePlayback ? currentScene?.interactive[0] : null;
    if (interactive?.cam_pos && interactive.cam_target && currentScene) {
      engine?.applyCameraPreset({ ...currentScene.camera, start_position: interactive.cam_pos, start_target: interactive.cam_target });
    }
  }

  return {
    ...narration,
    error: sceneError ?? narration.error,
    isMuted, setIsMuted, ccOn, setCcOn,
    captionText: captions.text,
    captionsError: captions.error,
    exploreMode, selectedHighlight, zoomed,
    hasSceneData: scenePlayback !== null,
    initialExploreMode: currentScene?.interactive[0]?.mode === "free" ? "free" as const : "standard" as const,
    toggleCameraView() {
      if (currentScene && engine?.applyCameraPreset(currentScene.camera, !zoomed)) setZoomed(!zoomed);
    },
    enterExplore(mode: ExploreMode) {
      pause();
      engine?.enterExplore(mode);
      if (exploreMode === null) applyInteractiveCamera();
      setExploreMode(mode);
    },
    resetExplore() { engine?.selectHighlight(null); engine?.resetExplore(); applyInteractiveCamera(); },
    exitExplore() { engine?.exitExplore(); setExploreMode(null); },
    closeHighlight() {
      const pose = highlightEntry.current;
      engine?.selectHighlight(null);
      if (pose) engine?.restoreCameraPose(pose);
    },
    restart() { seek(0); void narration.play(); },
    seekBy: (seconds: number) => seek(narration.currentTime + seconds),
  };
}
