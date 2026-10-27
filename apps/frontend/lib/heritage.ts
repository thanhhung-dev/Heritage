import { apiClient } from "@/config/api";
import type {
  ExploreArea,
  HeritagePayload,
  HeritageScene,
  HeritageSceneHighlight,
  HeritageSummary,
} from "@/types/heritage";

/**
 * Fetch published heritages for the homepage.
 *
 * Contract: `GET /api/heritages` → HeritageSummary[]
 */
export async function fetchHeritages(): Promise<HeritageSummary[]> {
  return apiClient<HeritageSummary[]>("/heritages");
}

/** Highlight có mốc thời gian trên timeline narration (giây). */
export type TimedHighlightData = HeritageSceneHighlight & {
  startSeconds: number;
  endSeconds: number | null;
};

/**
 * Audio + timing của một scene — mirror `playback` trong `tour.json`.
 * Cùng cấu trúc với `ScenePlayback` của player nên truyền thẳng vào context.
 */
export interface TourPlayback {
  narrationUrl: string | null;
  captionsUrl: string | null;
  timedHighlights: TimedHighlightData[];
  exploreArea: ExploreArea | null;
  exploreTitle: string | null;
  exploreDescription: string | null;
}

/** Toàn bộ dữ liệu tour trong một request — giống fixture `tour.json`. */
export interface TourContent {
  modelUrl: string | null;
  payload: HeritagePayload;
  playback: Record<string, TourPlayback>;
}

/**
 * Fetch payload + playback cho tour.
 *
 * Contract: `GET /api/heritages/{slug}/tour` → { modelUrl, payload, playback }
 * `playback` được khoá theo scene key ("s0".."sN"), đúng thứ tự route.
 */
export async function fetchTourContent(slug: string): Promise<TourContent> {
  return apiClient<TourContent>(`/heritages/${encodeURIComponent(slug)}/tour`);
}

/**
 * Map a URL scene key ("s0".."sN") to its backing scene.
 *
 * Routing convention (mirrors CyArk /content/{slug}):
 *   - "s0"  → overview (sequence -1)
 *   - "s1".."sN" → scenes[0..N-1] by index
 *
 * Returns null when the key is unknown or out of range.
 */
export function resolveSceneByKey(
  payload: HeritagePayload | null | undefined,
  sceneKey: string | undefined
): HeritageScene | null {
  if (!payload) return null;
  if (sceneKey === "s0") return payload.overview;
  const match = /^s(\d+)$/.exec(sceneKey ?? "");
  if (!match) return null;
  const index = Number(match[1]) - 1;
  return payload.scenes[index] ?? null;
}

/** Ordered scene keys for a payload, starting at "s0". */
export function sceneKeys(payload: HeritagePayload | null | undefined): string[] {
  if (!payload) return [];
  return ["s0", ...payload.scenes.map((_, i) => `s${i + 1}`)];
}

/** Scene key for a scene object (derives from its backend slug / sequence). */
export function sceneKeyOf(scene: HeritageScene): string {
  return scene.slug;
}
