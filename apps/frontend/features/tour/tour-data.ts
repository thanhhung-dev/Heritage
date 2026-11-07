import fixture from "./tour.json";
import type { ExploreArea, HeritagePayload } from "@/types/heritage";
import type { TimedSceneHighlight } from "./three/scene-highlights";

export interface ScenePlayback {
  narrationUrl: string | null;
  captionsUrl: string | null;
  timedHighlights: TimedSceneHighlight[];
  exploreArea: ExploreArea | null;
  exploreTitle: string | null;
  exploreDescription: string | null;
}

export const TEST_TOUR: {
  modelUrl: string;
  payload: HeritagePayload;
  playback: Record<string, ScenePlayback>;
} = fixture;
