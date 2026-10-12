import fixture from "./tour.json";
import type { HeritagePayload } from "@/types/heritage";
import type { TimedSceneHighlight } from "./three/scene-highlights";

export interface ScenePlayback {
  narrationUrl: string | null;
  captionsUrl: string | null;
  timedHighlights: TimedSceneHighlight[];
  exploreArea: { center: number[]; extents: number[]; rotation: number[] } | null;
}

// Fixture tách khỏi contract backend; chỉ dùng ở /content/tapestry-test.
export const TEST_TOUR: {
  modelUrl: string;
  payload: HeritagePayload;
  playback: Record<string, ScenePlayback>;
} = fixture;
