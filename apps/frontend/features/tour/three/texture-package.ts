/**
 * Tách gói texture nhỏ khỏi GLB có KTX2 nhúng.
 *
 * Mip 4K nằm cuối mỗi ảnh Basis. Gói preview chỉ giữ mip ≤ 256px (vài chục KB/ảnh)
 * cộng mesh. File đầy đủ của ảnh kéo sau, khi model đã hiện.
 */

export const PREVIEW_TEXTURE_MAX = 256;
const KTX2_ID = [0xab, 0x4b, 0x54, 0x58, 0x20, 0x32, 0x30, 0xbb, 0x0d, 0x0a, 0x1a, 0x0a];

export type GltfBufferView = {
  buffer?: number;
  byteOffset?: number;
  byteLength: number;
  byteStride?: number;
  target?: number;
};

export type GltfJson = {
  buffers?: { byteLength: number }[];
  bufferViews?: GltfBufferView[];
  images?: { mimeType?: string; bufferView?: number; name?: string; uri?: string }[];
  textures?: { name?: string; source?: number }[];
  extensionsUsed?: string[];
  extensionsRequired?: string[];
};

export type EmbeddedImage = {
  index: number;
  bufferView: number;
  byteOffset: number;
  byteLength: number;
};

export type TextureBinding = {
  material: number;
  slot: "map" | "normalMap" | "metalnessMap" | "roughnessMap" | "aoMap" | "emissiveMap";
  image: number;
};

type GltfTextureRef = { index?: number };
type GltfMaterial = {
  pbrMetallicRoughness?: {
    baseColorTexture?: GltfTextureRef;
    metallicRoughnessTexture?: GltfTextureRef;
  };
  normalTexture?: GltfTextureRef;
  occlusionTexture?: GltfTextureRef;
  emissiveTexture?: GltfTextureRef;
};

function imageOf(json: GltfJson, textureIndex: number | undefined) {
  if (textureIndex == null) return null;
  const source = json.textures?.[textureIndex]?.source;
  return source ?? null;
}

/** Bỏ mọi ảnh khỏi JSON để parser chỉ dựng khung mesh. Giữ plan để gắn texture sau. */
export function detachTextures(json: GltfJson): { json: GltfJson; plan: TextureBinding[] } {
  const next = structuredClone(json);
  const plan: TextureBinding[] = [];
  const materials = (next as GltfJson & { materials?: GltfMaterial[] }).materials ?? [];
  materials.forEach((material, materialIndex) => {
    const pbr = material.pbrMetallicRoughness;
    const base = imageOf(json, pbr?.baseColorTexture?.index);
    const packed = imageOf(json, pbr?.metallicRoughnessTexture?.index);
    const normal = imageOf(json, material.normalTexture?.index);
    const occlusion = imageOf(json, material.occlusionTexture?.index);
    const emissive = imageOf(json, material.emissiveTexture?.index);
    if (base != null) plan.push({ material: materialIndex, slot: "map", image: base });
    if (packed != null) {
      plan.push({ material: materialIndex, slot: "metalnessMap", image: packed });
      plan.push({ material: materialIndex, slot: "roughnessMap", image: packed });
    }
    if (normal != null) plan.push({ material: materialIndex, slot: "normalMap", image: normal });
    if (occlusion != null) plan.push({ material: materialIndex, slot: "aoMap", image: occlusion });
    if (emissive != null) plan.push({ material: materialIndex, slot: "emissiveMap", image: emissive });
    if (pbr) {
      delete pbr.baseColorTexture;
      delete pbr.metallicRoughnessTexture;
    }
    delete material.normalTexture;
    delete material.occlusionTexture;
    delete material.emissiveTexture;
  });
  next.images = [];
  next.textures = [];
  next.extensionsUsed = (next.extensionsUsed ?? []).filter((name) => name !== "KHR_texture_basisu" && name !== "EXT_texture_webp" && name !== "EXT_texture_avif");
  next.extensionsRequired = (next.extensionsRequired ?? []).filter((name) => name !== "KHR_texture_basisu" && name !== "EXT_texture_webp" && name !== "EXT_texture_avif");
  return { json: next, plan };
}

export function embeddedKtx2Images(json: GltfJson): EmbeddedImage[] {
  const views = json.bufferViews ?? [];
  const images: EmbeddedImage[] = [];
  for (let index = 0; index < (json.images ?? []).length; index += 1) {
    const image = json.images?.[index];
    if (!image || image.uri || image.bufferView == null || image.mimeType !== "image/ktx2") continue;
    const view = views[image.bufferView];
    if (!view) continue;
    images.push({
      index,
      bufferView: image.bufferView,
      byteOffset: view.byteOffset ?? 0,
      byteLength: view.byteLength,
    });
  }
  return images;
}

function isKtx2(bytes: Uint8Array) {
  if (bytes.byteLength < 80) return false;
  return KTX2_ID.every((byte, index) => bytes[index] === byte);
}

/** Số byte đầu của file KTX2 đủ để transcode mọi mip ≤ `maxSize`. */
export function ktx2PrefixLength(bytes: Uint8Array, maxSize: number): number | null {
  if (!isKtx2(bytes)) return null;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const width = view.getUint32(20, true);
  const height = view.getUint32(24, true);
  const levels = view.getUint32(40, true);
  if (levels < 1 || 80 + levels * 24 > bytes.byteLength) return null;
  let start = levels - 1;
  for (let level = 0; level < levels; level += 1) {
    if (Math.max(Math.max(1, width >> level), Math.max(1, height >> level)) <= maxSize) {
      start = level;
      break;
    }
  }
  let end = 80 + levels * 24;
  for (let level = start; level < levels; level += 1) {
    const offset = 80 + level * 24;
    const byteOffset = Number(view.getBigUint64(offset, true));
    const byteLength = Number(view.getBigUint64(offset + 8, true));
    end = Math.max(end, byteOffset + byteLength);
  }
  const dfdEnd = view.getUint32(48, true) + view.getUint32(52, true);
  const kvdEnd = view.getUint32(56, true) + view.getUint32(60, true);
  const sgdEnd = Number(view.getBigUint64(64, true)) + Number(view.getBigUint64(72, true));
  return Math.max(end, dfdEnd, kvdEnd, sgdEnd);
}

/** Cắt mip lớn khỏi KTX2 và sửa level index. Trả về chính `bytes` nếu không cắt được. */
export function trimKtx2(bytes: Uint8Array, maxSize: number): Uint8Array {
  const needed = ktx2PrefixLength(bytes, maxSize);
  if (needed == null || needed >= bytes.byteLength) return bytes;
  const source = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const levels = source.getUint32(40, true);
  const width = source.getUint32(20, true);
  const height = source.getUint32(24, true);
  let start = levels - 1;
  for (let level = 0; level < levels; level += 1) {
    if (Math.max(Math.max(1, width >> level), Math.max(1, height >> level)) <= maxSize) {
      start = level;
      break;
    }
  }
  const out = new Uint8Array(needed);
  out.set(bytes.subarray(0, needed));
  const view = new DataView(out.buffer);
  const kept = levels - start;
  view.setUint32(40, kept, true);
  for (let level = 0; level < kept; level += 1) {
    const from = 80 + (start + level) * 24;
    const to = 80 + level * 24;
    out.set(bytes.subarray(from, from + 24), to);
  }
  return out;
}

function pad4(length: number) {
  return (length + 3) & ~3;
}

function jsonChunk(text: string) {
  const raw = new TextEncoder().encode(text);
  const length = pad4(raw.byteLength);
  const chunk = new Uint8Array(length);
  chunk.set(raw);
  chunk.fill(0x20, raw.byteLength);
  return chunk;
}

/**
 * Dựng GLB preview: mỗi bufferView giữ nguyên byte bên trong, ảnh KTX2 đã cắt
 * được ghi tên `pkg-image-N` để lát nữa thay bằng bản đầy đủ.
 */
export function assemblePreviewGlb(json: GltfJson, viewBytes: Map<number, Uint8Array>): Uint8Array {
  const views = json.bufferViews ?? [];
  const order = views.map((view, index) => ({ index, offset: view.byteOffset ?? 0 }));
  order.sort((a, b) => a.offset - b.offset || a.index - b.index);
  const next = structuredClone(json);
  const placed: { index: number; bytes: Uint8Array }[] = [];
  let cursor = 0;
  for (const item of order) {
    const bytes = viewBytes.get(item.index);
    if (!bytes) throw new Error(`Thiếu bufferView ${item.index}`);
    cursor = pad4(cursor);
    const view = next.bufferViews?.[item.index];
    if (!view) throw new Error(`Thiếu mô tả bufferView ${item.index}`);
    view.byteOffset = cursor;
    view.byteLength = bytes.byteLength;
    placed.push({ index: item.index, bytes });
    cursor += bytes.byteLength;
  }
  cursor = pad4(cursor);
  if (next.buffers?.[0]) next.buffers[0].byteLength = cursor;
  for (const image of next.images ?? []) {
    if (image.bufferView == null) continue;
    image.name = `pkg-image-${image.bufferView}`;
  }
  for (const texture of next.textures ?? []) {
    if (texture.source == null) continue;
    const image = next.images?.[texture.source];
    if (image?.bufferView == null) continue;
    texture.name = `pkg-image-${image.bufferView}`;
  }

  const jsonBytes = jsonChunk(JSON.stringify(next));
  const bin = new Uint8Array(cursor);
  for (const item of placed) {
    const offset = next.bufferViews?.[item.index]?.byteOffset ?? 0;
    bin.set(item.bytes, offset);
  }
  const total = 12 + 8 + jsonBytes.byteLength + 8 + bin.byteLength;
  const glb = new Uint8Array(total);
  const header = new DataView(glb.buffer);
  header.setUint32(0, 0x46546c67, true);
  header.setUint32(4, 2, true);
  header.setUint32(8, total, true);
  header.setUint32(12, jsonBytes.byteLength, true);
  header.setUint32(16, 0x4e4f534a, true);
  glb.set(jsonBytes, 20);
  const binHeader = 20 + jsonBytes.byteLength;
  header.setUint32(binHeader, bin.byteLength, true);
  header.setUint32(binHeader + 4, 0x004e4942, true);
  glb.set(bin, binHeader + 8);
  return glb;
}

export function glbBinStart(header: Uint8Array): number | null {
  if (header.byteLength < 20) return null;
  const view = new DataView(header.buffer, header.byteOffset, header.byteLength);
  if (view.getUint32(0, true) !== 0x46546c67) return null;
  const jsonLength = view.getUint32(12, true);
  return 20 + jsonLength + 8;
}
