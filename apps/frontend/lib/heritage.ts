import { apiClient } from "@/config/api";
import type { HeritagePayload, HeritageScene } from "@/types/heritage";

/**
 * Fetch the full single-load heritage payload for a slug.
 *
 * Contract: `GET /api/heritages/{slug}` → { heritage, overview, scenes }
 * Overview is the intro scene (sequence -1, slug "s0").
 */
export async function fetchHeritagePayload(slug: string): Promise<HeritagePayload> {
  return apiClient<HeritagePayload>(`/heritages/${encodeURIComponent(slug)}`);
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