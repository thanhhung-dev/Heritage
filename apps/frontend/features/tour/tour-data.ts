import fixture from "./tour.json";
import type { ExploreArea, HeritagePayload } from "@/types/heritage";
import type { TimedSceneHighlight } from "./three/scene-highlights";

export interface ScenePlayback {
  narrationUrl: string | null;
  captionsUrl: string | null;
  timedHighlights: TimedSceneHighlight[];
  /** OBB giới hạn vùng đi bộ của chế độ `free_explore`; `null` = không giới hạn. */
  exploreArea: ExploreArea | null;
  /** Tiêu đề hiện khi vào chế độ đi bộ, ví dụ "Explore the Forecourt". */
  exploreTitle: string | null;
  /** Đoạn mô tả hiện kèm tiêu đề khi vào chế độ đi bộ. */
  exploreDescription: string | null;
}

// Fixture tách khỏi contract backend; chỉ dùng ở /content/tapestry-test.
export const TEST_TOUR: {
  modelUrl: string;
  payload: HeritagePayload;
  playback: Record<string, ScenePlayback>;
} = fixture;
