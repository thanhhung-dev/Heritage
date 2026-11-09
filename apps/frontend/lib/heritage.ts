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
 * `playback` được khoá theo `scene.slug`, kể cả khi sequence bị khuyết.
 */
export async function fetchTourContent(slug: string): Promise<TourContent> {
  return apiClient<TourContent>(`/heritages/${encodeURIComponent(slug)}/tour`);
}

/**
 * Map a URL scene key to the API-provided scene slug, not its array index.
 * Missing sequences must not shift scene IDs or make up routes.
 *
 * Returns null when the key is unknown.
 */
export function resolveSceneByKey(
  payload: HeritagePayload | null | undefined,
  sceneKey: string | undefined
): HeritageScene | null {
  if (!payload) return null;
  if (payload.overview?.slug === sceneKey) return payload.overview;
  return payload.scenes.find((scene) => scene.slug === sceneKey) ?? null;
}

/** Available scene slugs in tour order, including the overview when present. */
export function sceneKeys(payload: HeritagePayload | null | undefined): string[] {
  if (!payload) return [];
  return [
    ...(payload.overview ? [payload.overview.slug] : []),
    ...payload.scenes.map((scene) => scene.slug),
  ];
}

/** Scene key for a scene object (derives from its backend slug / sequence). */
export function sceneKeyOf(scene: HeritageScene): string {
  return scene.slug;
}
