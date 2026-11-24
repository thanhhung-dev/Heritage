import assert from "node:assert/strict";
import test from "node:test";
import {
  assemblePreviewGlb,
  embeddedKtx2Images,
  ktx2PrefixLength,
  trimKtx2,
} from "../features/tour/three/texture-package";

function ktx2(levels: { offset: number; length: number }[], width = 4096) {
  const bytes = new Uint8Array(1024);
  bytes.set([0xab, 0x4b, 0x54, 0x58, 0x20, 0x32, 0x30, 0xbb, 0x0d, 0x0a, 0x1a, 0x0a]);
  const view = new DataView(bytes.buffer);
  view.setUint32(20, width, true);
  view.setUint32(24, width, true);
  view.setUint32(40, levels.length, true);
  view.setUint32(48, 80 + levels.length * 24, true);
  view.setUint32(52, 8, true);
  for (let i = 0; i < levels.length; i += 1) {
    const at = 80 + i * 24;
    view.setBigUint64(at, BigInt(levels[i].offset), true);
    view.setBigUint64(at + 8, BigInt(levels[i].length), true);
  }
  return bytes;
}

test("prefix stops at the 256px mip and trim drops the larger levels", () => {
  const file = ktx2([
    { offset: 800, length: 200 },
    { offset: 500, length: 100 },
    { offset: 300, length: 80 },
    { offset: 200, length: 40 },
    { offset: 120, length: 30 },
  ]);
  assert.equal(ktx2PrefixLength(file, 256), 208);
  const trimmed = trimKtx2(file, 256);
  assert.equal(trimmed.byteLength, 208);
  const view = new DataView(trimmed.buffer);
  assert.equal(view.getUint32(40, true), 1);
  assert.equal(Number(view.getBigUint64(80, true)), 120);
  assert.equal(Number(view.getBigUint64(88, true)), 30);
});

test("preview GLB keeps mesh bytes and renames the trimmed image", () => {
  const mesh = new Uint8Array([1, 2, 3, 4]);
  const image = new Uint8Array([9, 9]);
  const glb = assemblePreviewGlb({
    buffers: [{ byteLength: 1 }],
    bufferViews: [
      { byteOffset: 0, byteLength: 4, target: 34962 },
      { byteOffset: 8, byteLength: 2 },
    ],
    images: [{ mimeType: "image/ktx2", bufferView: 1 }],
    textures: [{ source: 0 }],
  }, new Map([[0, mesh], [1, image]]));
  const view = new DataView(glb.buffer);
  assert.equal(view.getUint32(0, true), 0x46546c67);
  const jsonLength = view.getUint32(12, true);
  const json = JSON.parse(new TextDecoder().decode(glb.subarray(20, 20 + jsonLength)));
  assert.equal(json.images[0].name, "pkg-image-1");
  assert.equal(json.textures[0].name, "pkg-image-1");
  assert.equal(json.bufferViews[1].byteLength, 2);
  assert.equal(embeddedKtx2Images(json)[0]?.bufferView, 1);
  const binAt = 20 + jsonLength + 8;
  assert.deepEqual([...glb.subarray(binAt, binAt + 4)], [1, 2, 3, 4]);
});
