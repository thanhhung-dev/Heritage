import { CompressedTexture, type Material, type Mesh } from "three";
import type { GLTF } from "three/addons/loaders/GLTFLoader.js";
import {
  assemblePreviewGlb,
  detachTextures,
  embeddedKtx2Images,
  glbBinStart,
  ktx2PrefixLength,
  trimKtx2,
  PREVIEW_TEXTURE_MAX,
  type GltfJson,
  type TextureBinding,
} from "./texture-package";


async function fetchRange(url: string, start: number, end: number, signal: AbortSignal) {
  const response = await fetch(url, {
    headers: { Range: `bytes=${start}-${end - 1}` },
    signal,
  });
  if (response.status !== 206) throw new Error("Server không cắt được gói byte");
  return new Uint8Array(await response.arrayBuffer());
}

/**
 * Tải mesh + mip ≤ 256px trước. `null` nếu file không phải GLB KTX2 nhúng hoặc
 * server không hỗ trợ Range — nơi gọi tải cả file như cũ.
 *
 * Bản mip lớn được gắn vào đúng material sau khi model đã trả về.
 */
export async function loadPreviewGlb(
  url: string,
  signal: AbortSignal,
  parseGlb: (bytes: ArrayBuffer) => Promise<GLTF>,
  parseKtx2: (bytes: ArrayBuffer) => Promise<CompressedTexture>,
  sharpen: (texture: CompressedTexture) => void,
  onProgress?: (loaded: number, total: number) => void,
): Promise<{ gltf: GLTF; settled: Promise<void> } | null> {
  const header = await fetchRange(url, 0, 20, signal);
  const binStart = glbBinStart(header);
  if (binStart == null) return null;
  const jsonBytes = await fetchRange(url, 20, binStart - 8, signal);
  const json = JSON.parse(new TextDecoder().decode(jsonBytes)) as GltfJson;
  const images = embeddedKtx2Images(json);
  if (images.length === 0) return null;

  const imageViews = new Set(images.map((image) => image.bufferView));
  const meshViews = (json.bufferViews ?? [])
    .map((view, index) => ({ index, byteOffset: view.byteOffset ?? 0, byteLength: view.byteLength }))
    .filter((view) => !imageViews.has(view.index));
  let meshBytes = 0;
  for (const view of meshViews) meshBytes += view.byteLength;
  onProgress?.(0, meshBytes);

  const meshPayload = new Map<number, Uint8Array>();
  const meshRanges = merged(meshViews);
  let loaded = 0;
  await Promise.all(meshRanges.map(async (range) => {
    const bytes = await fetchRange(url, binStart + range.start, binStart + range.end, signal);
    loaded += bytes.byteLength;
    onProgress?.(Math.min(loaded, meshBytes), meshBytes);
    for (const view of meshViews) {
      if (view.byteOffset < range.start || view.byteOffset + view.byteLength > range.end) continue;
      meshPayload.set(view.index, bytes.subarray(view.byteOffset - range.start, view.byteOffset - range.start + view.byteLength));
    }
  }));

  const frame = detachTextures(json);
  const viewBytes = new Map<number, Uint8Array>(meshPayload);
  for (const image of images) viewBytes.set(image.bufferView, new Uint8Array(4));
  const preview = assemblePreviewGlb(frame.json, viewBytes);
  const gltf = await parseGlb(preview.slice().buffer);
  const settled = upgrade(url, binStart, images, gltf, frame.plan, signal, parseKtx2, sharpen).then(
    () => undefined,
    () => undefined,
  );
  return { gltf, settled };
}

async function upgrade(
  url: string,
  binStart: number,
  images: { index: number; byteOffset: number; byteLength: number }[],
  gltf: GLTF,
  plan: TextureBinding[],
  signal: AbortSignal,
  parseKtx2: (bytes: ArrayBuffer) => Promise<CompressedTexture>,
  sharpen: (texture: CompressedTexture) => void,
) {
  const blurry = new Map<number, CompressedTexture>();
  await Promise.all(images.map(async (image) => {
    const probe = await fetchRange(
      url,
      binStart + image.byteOffset,
      binStart + image.byteOffset + Math.min(image.byteLength, 512),
      signal,
    );
    const prefix = ktx2PrefixLength(probe, PREVIEW_TEXTURE_MAX);
    if (prefix == null) return;
    const length = Math.min(image.byteLength, prefix);
    const bytes = length <= probe.byteLength
      ? probe.subarray(0, length)
      : await fetchRange(url, binStart + image.byteOffset, binStart + image.byteOffset + length, signal);
    const trimmed = trimKtx2(bytes, PREVIEW_TEXTURE_MAX);
    blurry.set(image.index, await parseKtx2(trimmed.slice().buffer));
  }));
  if (signal.aborted) return;
  applyPlan(gltf, plan, blurry);
  for (const texture of blurry.values()) sharpen(texture);

  const sharp = new Map<number, CompressedTexture>();
  await Promise.all(images.map(async (image) => {
    const bytes = await fetchRange(url, binStart + image.byteOffset, binStart + image.byteOffset + image.byteLength, signal);
    sharp.set(image.index, await parseKtx2(bytes.slice().buffer));
  }));
  if (signal.aborted) return;
  applyPlan(gltf, plan, sharp);
  for (const texture of sharp.values()) sharpen(texture);
}

function applyPlan(gltf: GLTF, plan: TextureBinding[], byImage: Map<number, CompressedTexture>) {
  const materials = new Map<number, Material>();
  gltf.scene.traverse((object) => {
    const mesh = object as Mesh;
    if (!mesh.isMesh) return;
    const list = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const material of list) {
      const index = gltf.parser.associations.get(material)?.materials;
      if (index != null) materials.set(index, material);
    }
  });
  for (const binding of plan) {
    const material = materials.get(binding.material);
    const texture = byImage.get(binding.image);
    if (!material || !texture) continue;
    Reflect.set(material, binding.slot, texture);
    material.needsUpdate = true;
  }
}

function merged(views: { byteOffset: number; byteLength: number }[]) {
  const sorted = [...views].sort((a, b) => a.byteOffset - b.byteOffset);
  const ranges: { start: number; end: number }[] = [];
  for (const view of sorted) {
    const start = view.byteOffset;
    const end = start + view.byteLength;
    const last = ranges[ranges.length - 1];
    if (last && start <= last.end + 4) last.end = Math.max(last.end, end);
    else ranges.push({ start, end });
  }
  return ranges;
}
