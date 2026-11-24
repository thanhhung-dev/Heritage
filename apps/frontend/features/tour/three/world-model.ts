import type { HeritageModelAsset, HeritageScene } from "@/types/heritage";

const GLB_EXT = /\.gltf?(?:$|[?#])/i;

/**
 * Model thế giới của một cảnh — GLB/glTF, không phải splat/SOG.
 *
 * Tapestry gắn mỗi cảnh vào một `threeJS_sets` (`asset` là file thế giới).
 * Ở đây file đó nằm ở `scene.models`: LOD thấp nhất, bỏ qua format khác GLB.
 */
export function isWorldModel(model: Pick<HeritageModelAsset, "file_url"> & { format?: string | null }): boolean {
  const url = model.file_url?.trim() ?? "";
  if (!url) return false;
  const format = (model.format ?? "").trim().toLowerCase();
  if (format === "glb" || format === "gltf") return true;
  if (format) return false;
  return GLB_EXT.test(url);
}

/**
 * File thế giới của cảnh.
 *
 * Ưu tiên GLB riêng trong `scene.models`. Không có thì cảnh
 * `use_interior_model` dùng `interiorUrl` (`heritage.interior_model_url`).
 * Còn lại là file mặc định của tour (ngoài / `modelUrl`).
 */
export function resolveWorldUrl(
  scene: (Pick<HeritageScene, "models"> & { use_interior_model?: boolean }) | null | undefined,
  fallbackUrl: string,
  interiorUrl?: string | null,
): string {
  const candidates = (scene?.models ?? [])
    .filter((model) => isWorldModel(model))
    .sort((a, b) => (a.lod_level ?? 0) - (b.lod_level ?? 0));
  if (candidates[0]?.file_url) return candidates[0].file_url;
  const interior = interiorUrl?.trim() ?? "";
  if (scene?.use_interior_model && interior) return interior;
  return fallbackUrl;
}
