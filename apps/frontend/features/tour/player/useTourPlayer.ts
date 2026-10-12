"use client";

import { useEffect, useState } from "react";
import { useHeritageTour } from "@/context/heritage-tour";
import type { HeritageInteractiveHighlight } from "@/types/heritage";
import type { ExploreMode } from "../three/explore-controller";
import { useNarration } from "./useNarration";
import { useCaptions } from "./useCaptions";

export function useTourPlayer({ narrationUrl = null, captionsUrl = null }: {
  narrationUrl?: string | null;
  captionsUrl?: string | null;
} = {}) {
  const { engine, currentSceneKey } = useHeritageTour();
  const [isMuted, setIsMuted] = useState(false);
  const [ccOn, setCcOn] = useState(true);
  const [exploreMode, setExploreMode] = useState<ExploreMode | null>(null);
  const [selectedHighlight, setSelectedHighlight] = useState<HeritageInteractiveHighlight | null>(null);
  const narration = useNarration(narrationUrl, isMuted);
  const captions = useCaptions(captionsUrl, narration.currentTime, ccOn);
  const { pause, seek } = narration;

  useEffect(() => {
    pause();
    seek(0);
    engine?.exitExplore();
    engine?.setInteractiveHighlights([]);
    void engine?.setSceneHighlights([]);
    setExploreMode(null);
    setSelectedHighlight(null);
    return engine?.onHighlightSelect(setSelectedHighlight);
  }, [engine, currentSceneKey, pause, seek]);
  useEffect(() => {
    engine?.setPlaybackTime(narration.currentTime);
  }, [engine, narration.currentTime]);

  return {
    ...narration,
    isMuted, setIsMuted, ccOn, setCcOn,
    captionText: captions.text,
    captionsError: captions.error,
    exploreMode, selectedHighlight,
    enterExplore(mode: ExploreMode) {
      pause();
      engine?.enterExplore(mode);
      setExploreMode(mode);
    },
    resetExplore: () => engine?.resetExplore(),
    exitExplore() { engine?.exitExplore(); setExploreMode(null); },
    closeHighlight: () => engine?.selectHighlight(null),
    restart() { seek(0); void narration.play(); },
    seekBy: (seconds: number) => seek(narration.currentTime + seconds),
  };
}
