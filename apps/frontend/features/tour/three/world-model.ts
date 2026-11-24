import type { HeritageModelAsset, HeritageScene } from "@/types/heritage";

const GLB_EXT = /\.gltf?(?:$|[?#])/i;

/**
 * Model thế giới của một cảnh — GLB/glTF, không phải splat/SOG.
 *
 * Tapestry gắn mỗi cảnh vào một `threeJS_sets` (`asset` là file thế giới).
 * Ở đây file đó nằm ở `scene.models`. Format khác GLB bị bỏ qua.
 */
export function isWorldModel(model: Pick<HeritageModelAsset, "file_url"> & { format?: string | null }): boolean {
  const url = model.file_url?.trim() ?? "";
  if (!url) return false;
  const format = (model.format ?? "").trim().toLowerCase();
  if (format === "glb" || format === "gltf") return true;
  if (format) return false;
  return GLB_EXT.test(url);
}

export type WorldFiles = {
  /** Bản thô, hiện ngay. Trùng `full` khi cảnh chỉ có một GLB. */
  preview: string;
  /** File đầy đủ. `lod_level` nhỏ nhất; hiện thay bản thô khi tải xong. */
  full: string;
};

function worldGlbs(
  scene: (Pick<HeritageScene, "models"> & { use_interior_model?: boolean }) | null | undefined,
) {
  return (scene?.models ?? [])
    .filter((model) => isWorldModel(model))
    .sort((a, b) => (a.lod_level ?? 0) - (b.lod_level ?? 0));
}

/**
 * Cặp file thế giới của cảnh.
 *
 * `scene.models` có nhiều GLB thì `full` là `lod_level` nhỏ nhất, `preview` là
 * mức cao nhất (bản thô). Một GLB, hoặc chỉ có `interior_model_url`, thì hai
 * URL trùng nhau — không có bản thô để hiện trước.
 */
export function resolveWorldFiles(
  scene: (Pick<HeritageScene, "models"> & { use_interior_model?: boolean }) | null | undefined,
  fallbackUrl: string,
  interiorUrl?: string | null,
): WorldFiles {
  const glbs = worldGlbs(scene);
  if (glbs.length > 0) {
    const full = glbs[0].file_url.trim();
    const preview = glbs[glbs.length - 1].file_url.trim();
    return { preview, full };
  }
  const interior = interiorUrl?.trim() ?? "";
  if (scene?.use_interior_model && interior) return { preview: interior, full: interior };
  return { preview: fallbackUrl, full: fallbackUrl };
}

/**
 * File thế giới đầy đủ của cảnh.
 *
 * Ưu tiên GLB `lod_level` nhỏ nhất trong `scene.models`. Không có thì cảnh
 * `use_interior_model` dùng `interiorUrl` (`heritage.interior_model_url`).
 * Còn lại là file mặc định của tour (ngoài / `modelUrl`).
 */
export function resolveWorldUrl(
  scene: (Pick<HeritageScene, "models"> & { use_interior_model?: boolean }) | null | undefined,
  fallbackUrl: string,
  interiorUrl?: string | null,
): string {
  return resolveWorldFiles(scene, fallbackUrl, interiorUrl).full;
}
