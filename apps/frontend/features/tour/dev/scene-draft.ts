import type { HeritageScene } from "@/types/heritage";

type Vec3 = [number, number, number];

export interface EditorPose {
  position: Vec3;
  target: Vec3;
  up: Vec3;
  fov: number;
}

/** Local authoring document, not a backend request or a published camera path. */
export interface SceneDraft {
  version: 1;
  heritageSlug: string;
  sceneId: number;
  sceneKey: string;
  title: string;
  description: string;
  start: EditorPose | null;
  end: EditorPose | null;
  durationSeconds: number;
  useAB: boolean;
}

function vector(value: unknown): Vec3 | null {
  if (!value || typeof value !== "object") return null;
  const xyz = Array.isArray(value) ? value : Object.values({
    x: (value as Record<string, unknown>).x,
    y: (value as Record<string, unknown>).y,
    z: (value as Record<string, unknown>).z,
  });
  return xyz.length === 3 && xyz.every((n) => typeof n === "number" && Number.isFinite(n))
    ? [xyz[0], xyz[1], xyz[2]] as Vec3 : null;
}

function pose(position: unknown, target: unknown): EditorPose | null {
  const p = vector(position);
  const t = vector(target);
  return p && t ? { position: p, target: t, up: [0, 1, 0], fov: 50 } : null;
}

export function createSceneDraft(heritageSlug: string, sceneKey: string, scene: HeritageScene): SceneDraft {
  return {
    version: 1, heritageSlug, sceneId: scene.id, sceneKey,
    title: scene.title, description: scene.description ?? "",
    start: pose(scene.camera.start_position, scene.camera.start_target),
    end: pose(scene.camera.zoom_position, scene.camera.zoom_target),
    durationSeconds: 12, useAB: !scene.camera.path_url,
  };
}

function validPose(value: unknown): boolean {
  if (value === null) return true;
  if (!value || typeof value !== "object") return false;
  const p = value as EditorPose;
  return !!vector(p.position) && !!vector(p.target) && !!vector(p.up) &&
    typeof p.fov === "number" && Number.isFinite(p.fov) && p.fov >= 10 && p.fov <= 120 &&
    p.position.some((n, i) => n !== p.target[i]) && p.up.some((n) => n !== 0);
}

export function parseSceneDraft(raw: string, heritageSlug: string, sceneKey: string, sceneId: number): SceneDraft | null {
  try {
    const d = JSON.parse(raw) as SceneDraft | null;
    if (!d || d.version !== 1 || d.heritageSlug !== heritageSlug || d.sceneKey !== sceneKey || d.sceneId !== sceneId ||
      typeof d.title !== "string" || typeof d.description !== "string" || typeof d.useAB !== "boolean" ||
      typeof d.durationSeconds !== "number" || !Number.isFinite(d.durationSeconds) || d.durationSeconds <= 0 ||
      !validPose(d.start) || !validPose(d.end)) return null;
    return d;
  } catch {
    return null;
  }
}

/** Absolute-time preview: scrubbing backwards is identical to playing forwards. */
export function sampleSceneDraft(draft: SceneDraft, seconds: number): EditorPose | null {
  if (!draft.start || !draft.end || !draft.useAB) return null;
  const t = Math.max(0, Math.min(1, seconds / draft.durationSeconds));
  const lerp = (a: Vec3, b: Vec3): Vec3 => a.map((n, i) => n + (b[i] - n) * t) as Vec3;
  return {
    position: lerp(draft.start.position, draft.end.position),
    target: lerp(draft.start.target, draft.end.target),
    up: lerp(draft.start.up, draft.end.up),
    fov: draft.start.fov + (draft.end.fov - draft.start.fov) * t,
  };
}
