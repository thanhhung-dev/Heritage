/**
 * ktx2-to-png.mjs — chuyển GLB dùng KHR_texture_basisu (KTX2) sang GLB dùng PNG
 * để Blender mở được (glTF addon của Blender 4.x không giải mã KTX2).
 *
 * Chỉ đổi phần ảnh. Hình học, UV, material, node, Draco... giữ nguyên tuyệt đối
 * vì bufferView của geometry được copy nguyên byte.
 *
 *   node tools/terrain-gen/ktx2-to-png.mjs <in.glb> <out.glb> [--max 2048] [--level 6]
 *
 * --max   cạnh lớn nhất của ảnh sau khi thu nhỏ (0 = giữ nguyên 4096). Mặc định 2048.
 * --level mức nén zlib của PNG (0-9). Mặc định 6.
 *
 * Ảnh không phải KTX2 (JPEG/PNG có sẵn) được giữ nguyên, không encode lại.
 */
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const BASIS = require(path.join(here, "../../apps/frontend/public/three/basis/basis_transcoder.js"));

const CTF_RGBA32 = 13;

/* ------------------------------- PNG encoder ------------------------------ */
const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
})();

function crc32(buf) {
  let crc = 0xffffffff;
  for (let i = 0; i < buf.length; i += 1) crc = CRC_TABLE[(crc ^ buf[i]) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
  const head = Buffer.alloc(8);
  head.writeUInt32BE(data.length, 0);
  head.write(type, 4, "ascii");
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([head.subarray(4), data])), 0);
  return Buffer.concat([head, data, crc]);
}

/** PNG RGB8 (bỏ alpha) với filter "Up" — nén tốt hơn filter None mà vẫn nhanh. */
function encodePngRgb(width, height, rgba, level = 6) {
  const stride = width * 3;
  const raw = Buffer.alloc((stride + 1) * height);
  let prev = Buffer.alloc(stride);
  for (let y = 0; y < height; y += 1) {
    const out = y * (stride + 1);
    raw[out] = 2; // filter Up
    const line = Buffer.alloc(stride);
    let src = y * width * 4;
    for (let x = 0, d = 0; x < width; x += 1, d += 3, src += 4) {
      line[d] = rgba[src];
      line[d + 1] = rgba[src + 1];
      line[d + 2] = rgba[src + 2];
    }
    for (let i = 0; i < stride; i += 1) raw[out + 1 + i] = (line[i] - prev[i]) & 0xff;
    prev = line;
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = 2;
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    pngChunk("IHDR", ihdr),
    pngChunk("IDAT", zlib.deflateSync(raw, { level })),
    pngChunk("IEND", Buffer.alloc(0)),
  ]);
}

/** Thu nhỏ bằng box filter theo hệ số nguyên (giữ đúng màu trung bình, không gây răng cưa). */
function downscale(rgba, w, h, factor) {
  if (factor <= 1) return { data: rgba, width: w, height: h };
  const nw = Math.floor(w / factor);
  const nh = Math.floor(h / factor);
  const out = new Uint8Array(nw * nh * 4);
  const n = factor * factor;
  for (let y = 0; y < nh; y += 1) {
    for (let x = 0; x < nw; x += 1) {
      let r = 0, g = 0, b = 0, a = 0;
      for (let dy = 0; dy < factor; dy += 1) {
        let src = ((y * factor + dy) * w + x * factor) * 4;
        for (let dx = 0; dx < factor; dx += 1) {
          r += rgba[src]; g += rgba[src + 1]; b += rgba[src + 2]; a += rgba[src + 3];
          src += 4;
        }
      }
      const dst = (y * nw + x) * 4;
      out[dst] = r / n; out[dst + 1] = g / n; out[dst + 2] = b / n; out[dst + 3] = a / n;
    }
  }
  return { data: out, width: nw, height: nh };
}

/* --------------------------------- GLB I/O -------------------------------- */
function readGlb(file) {
  const buf = fs.readFileSync(file);
  if (buf.readUInt32LE(0) !== 0x46546c67) throw new Error("Không phải GLB");
  let off = 12;
  let json = null;
  let bin = Buffer.alloc(0);
  while (off < buf.length) {
    const len = buf.readUInt32LE(off);
    const type = buf.readUInt32LE(off + 4);
    const data = buf.subarray(off + 8, off + 8 + len);
    if (type === 0x4e4f534a) json = JSON.parse(data.toString("utf8"));
    else if (type === 0x004e4942) bin = data;
    off += 8 + len;
  }
  return { json, bin };
}

function writeGlb(file, json, bin) {
  let text = Buffer.from(JSON.stringify(json), "utf8");
  if (text.length % 4) text = Buffer.concat([text, Buffer.alloc(4 - (text.length % 4), 0x20)]);
  const padBin = bin.length % 4 ? Buffer.concat([bin, Buffer.alloc(4 - (bin.length % 4))]) : bin;
  const total = 12 + 8 + text.length + 8 + padBin.length;
  const out = Buffer.alloc(total);
  out.writeUInt32LE(0x46546c67, 0);
  out.writeUInt32LE(2, 4);
  out.writeUInt32LE(total, 8);
  out.writeUInt32LE(text.length, 12);
  out.writeUInt32LE(0x4e4f534a, 16);
  text.copy(out, 20);
  let off = 20 + text.length;
  out.writeUInt32LE(padBin.length, off);
  out.writeUInt32LE(0x004e4942, off + 4);
  padBin.copy(out, off + 8);
  fs.writeFileSync(file, out);
}

/* ---------------------------------- main ---------------------------------- */
const argv = process.argv.slice(2);
const input = argv[0];
const output = argv[1];
const maxArg = argv.indexOf("--max");
const levelArg = argv.indexOf("--level");
const MAX = maxArg >= 0 ? Number(argv[maxArg + 1]) : 2048;
const LEVEL = levelArg >= 0 ? Number(argv[levelArg + 1]) : 6;

if (!input || !output) {
  console.error("dùng: node tools/terrain-gen/ktx2-to-png.mjs <in.glb> <out.glb> [--max 2048] [--level 6]");
  process.exit(1);
}

const { json, bin } = readGlb(input);
const basis = await BASIS();
basis.initializeBasis(); // bắt buộc, thiếu là KTX2File.isValid() luôn false

const pngByView = new Map();
let converted = 0;

for (let i = 0; i < json.images.length; i += 1) {
  const image = json.images[i];
  if (image.mimeType !== "image/ktx2") {
    console.log(`  [${i}] ${image.mimeType} — giữ nguyên`);
    continue;
  }
  const view = json.bufferViews[image.bufferView];
  const start = view.byteOffset ?? 0;
  const file = new basis.KTX2File(new Uint8Array(bin.subarray(start, start + view.byteLength)));
  if (!file.isValid()) throw new Error(`KTX2 không hợp lệ: ${image.name}`);
  if (!file.startTranscoding()) throw new Error(`startTranscoding lỗi: ${image.name}`);

  const info = file.getImageLevelInfo(0, 0, 0);
  const size = file.getImageTranscodedSizeInBytes(0, 0, 0, CTF_RGBA32);
  const dst = new Uint8Array(size);
  if (!file.transcodeImage(dst, 0, 0, 0, CTF_RGBA32, 0, -1, -1)) {
    throw new Error(`transcodeImage lỗi: ${image.name}`);
  }
  file.close();

  const factor = MAX > 0 ? Math.ceil(Math.max(info.width, info.height) / MAX) : 1;
  const small = downscale(dst, info.width, info.height, factor);
  const png = encodePngRgb(small.width, small.height, small.data, LEVEL);

  pngByView.set(image.bufferView, png);
  image.mimeType = "image/png";
  converted += 1;
  console.log(
    `  [${i}] ${(image.name ?? "").padEnd(26)} ${info.width}x${info.height}` +
    ` → ${small.width}x${small.height} PNG ${(png.length / 1024 / 1024).toFixed(2)} MB`,
  );
}

if (!converted) {
  console.log("Không có ảnh KTX2 nào — file này mở được bằng Blender rồi.");
  process.exit(0);
}

// Dựng lại BIN: giữ nguyên mọi bufferView, chỉ thay bufferView của ảnh.
const chunks = [];
let cursor = 0;
const pad4 = (n) => (n + 3) & ~3;
for (let i = 0; i < json.bufferViews.length; i += 1) {
  const view = json.bufferViews[i];
  const data = pngByView.has(i)
    ? pngByView.get(i)
    : bin.subarray(view.byteOffset ?? 0, (view.byteOffset ?? 0) + view.byteLength);
  const offset = pad4(cursor);
  if (offset > cursor) chunks.push(Buffer.alloc(offset - cursor));
  view.byteOffset = offset;
  view.byteLength = data.length;
  chunks.push(Buffer.from(data));
  cursor = offset + data.length;
}
const newBin = Buffer.concat(chunks);

for (const texture of json.textures) {
  const src = texture.extensions?.KHR_texture_basisu?.source;
  if (src !== undefined) {
    delete texture.extensions.KHR_texture_basisu;
    if (!Object.keys(texture.extensions).length) delete texture.extensions;
    texture.source = src;
  }
}
for (const key of ["extensionsUsed", "extensionsRequired"]) {
  if (!json[key]) continue;
  json[key] = json[key].filter((n) => n !== "KHR_texture_basisu");
  if (!json[key].length) delete json[key];
}
json.buffers[0].byteLength = newBin.length;

writeGlb(output, json, newBin);

const inMb = fs.statSync(input).size / 1024 / 1024;
const outMb = fs.statSync(output).size / 1024 / 1024;
console.log(`\n${input}  ${inMb.toFixed(1)} MB`);
console.log(`${output}  ${outMb.toFixed(1)} MB  (${converted} ảnh KTX2 → PNG)`);
console.log(`extensionsUsed: ${JSON.stringify(json.extensionsUsed ?? [])}`);
