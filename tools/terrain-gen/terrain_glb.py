#!/usr/bin/env python3
"""
terrain_glb.py - sinh mot lop dia hinh (GLB) cho bat ky toa do nao.

Nguon du lieu (mien phi, khong can API key):
  - Do cao : AWS Terrain Tiles (terrarium PNG), nguon SRTM/ASTER/GMTED ~30 m.
  - Anh nen: ESRI World Imagery, mot request duy nhat qua endpoint `export`.

Ket qua la GLB Y-up, don vi met, goc toa do o tam o vuong, Y=0 tai diem thap nhat.
Dung de gan vao scene 3D cua tour theo dung cach Tapestry lam voi Petra:
mot node "gcontext" rieng, UV chieu phang, chi co albedo.

  python tools/terrain-gen/terrain_glb.py --lat 16.4697 --lng 107.5785 \
      --size 2000 --grid 192 --tex 3000 --out terrain.glb

Chi can numpy + requests (khong can GDAL/Pillow).
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import struct
import sys
import time
import zlib

import numpy as np
import requests

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

EARTH_R = 6378137.0
TILE = 256
M_PER_DEG_LAT = 110574.0
M_PER_DEG_LNG_EQ = 111320.0
UA = {"User-Agent": "HeritageGraph-terrain-gen/1.0 (dev tool)"}

DEM_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
IMG_URL = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
IMG_MAX = 3000  # endpoint tra 500 khi > ~3500 px


# --------------------------------------------------------------------------
# PNG doc bang stdlib (chi de giai ma tile DEM, anh nen giu nguyen JPEG)
# --------------------------------------------------------------------------

def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def decode_png(blob: bytes) -> np.ndarray:
    """Tra ve array (h, w, channels) uint8. Ho tro bit depth 8, khong interlace."""
    if blob[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("khong phai PNG")
    pos, idat, plte = 8, [], None
    width = height = depth = ctype = interlace = 0
    while pos < len(blob):
        (length,) = struct.unpack_from(">I", blob, pos)
        ctype_name = blob[pos + 4:pos + 8]
        data = blob[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype_name == b"IHDR":
            width, height, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", data)
        elif ctype_name == b"PLTE":
            plte = np.frombuffer(data, dtype=np.uint8).reshape(-1, 3)
        elif ctype_name == b"IDAT":
            idat.append(data)
        elif ctype_name == b"IEND":
            break
    if depth != 8 or interlace != 0:
        raise ValueError(f"PNG khong ho tro: depth={depth} interlace={interlace}")

    ch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    raw = zlib.decompress(b"".join(idat))
    stride = width * ch
    out = np.empty((height, stride), dtype=np.uint8)
    prev = np.zeros(stride, dtype=np.int32)
    src = 0
    for row in range(height):
        f = raw[src]
        src += 1
        line = np.frombuffer(raw, dtype=np.uint8, count=stride, offset=src).astype(np.int32)
        src += stride
        if f == 0:
            cur = line
        elif f == 1:
            cur = line.copy()
            for i in range(ch, stride):
                cur[i] = (cur[i] + cur[i - ch]) & 0xFF
        elif f == 2:
            cur = (line + prev) & 0xFF
        elif f == 3:
            cur = line.copy()
            for i in range(stride):
                left = cur[i - ch] if i >= ch else 0
                cur[i] = (cur[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif f == 4:
            cur = line.copy()
            for i in range(stride):
                a = cur[i - ch] if i >= ch else 0
                c = prev[i - ch] if i >= ch else 0
                cur[i] = (cur[i] + _paeth(a, prev[i], c)) & 0xFF
        else:
            raise ValueError(f"filter la: {f}")
        out[row] = cur.astype(np.uint8)
        prev = cur
    img = out.reshape(height, width, ch)
    if ctype == 3:
        img = plte[img[:, :, 0]]
    return img


def encode_png_rgb(rgb: np.ndarray) -> bytes:
    """PNG RGB8 toi gian (filter 0) - dung cho anh preview."""
    h, w, _ = rgb.shape
    raw = np.zeros((h, w * 3 + 1), dtype=np.uint8)
    raw[:, 1:] = rgb.reshape(h, w * 3)
    comp = zlib.compress(raw.tobytes(), 6)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# --------------------------------------------------------------------------
# DEM: tile terrarium
# --------------------------------------------------------------------------

def lonlat_to_tile(lat: float, lng: float, z: int) -> tuple[float, float]:
    n = 2 ** z
    x = (lng + 180.0) / 360.0 * n
    lat_r = math.radians(max(-85.05, min(85.05, lat)))
    y = (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n
    return x, y


def _cached_get(url: str, cache_dir: str, suffix: str, retries: int = 3,
                timeout: int = 60) -> bytes:
    os.makedirs(cache_dir, exist_ok=True)
    key = url.split("://", 1)[1].replace("/", "_").replace("?", "_").replace("&", "_")
    path = os.path.join(cache_dir, key[:180] + suffix)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "rb") as fh:
            return fh.read()
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=UA, timeout=timeout)
            if r.status_code == 200 and len(r.content) > 0:
                with open(path, "wb") as fh:
                    fh.write(r.content)
                return r.content
            last = f"HTTP {r.status_code}"
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"tai that bai {url} ({last})")


def fetch_dem(lat: float, lng: float, half_m: float, cache_dir: str,
              zoom: int | None = None,
              target_mpp: float | None = None) -> tuple[np.ndarray, dict]:
    """Mosaic cac tile terrarium phu o vuong, tra ve (array do cao, bounds)."""
    coslat = math.cos(math.radians(lat))
    dlat = half_m / M_PER_DEG_LAT
    dlng = half_m / (M_PER_DEG_LNG_EQ * coslat)
    north, south = lat + dlat, lat - dlat
    west, east = lng - dlng, lng + dlng

    if zoom is None:
        # Chon zoom gan voi do phan giai goc cua DEM (~30 m) nhat. Lay zoom
        # qua cao chi khuech dai nhieu noi suy cua SRTM, khong them chi tiet.
        want = max(target_mpp or 30.0, 18.0)
        zoom = min(range(8, 16),
                   key=lambda z: abs(156543.03392 * coslat / (2 ** z) - want))

    x0, y0 = lonlat_to_tile(north, west, zoom)
    x1, y1 = lonlat_to_tile(south, east, zoom)
    tx0, ty0 = int(math.floor(x0)), int(math.floor(y0))
    tx1, ty1 = int(math.floor(x1)), int(math.floor(y1))
    nx, ny = tx1 - tx0 + 1, ty1 - ty0 + 1
    print(f"  DEM z={zoom} ({156543.03392 * coslat / 2 ** zoom:.1f} m/px) "
          f"-> {nx}x{ny} tile")

    mosaic = np.zeros((ny * TILE, nx * TILE), dtype=np.float32)
    ok = 0
    for ty in range(ty0, ty1 + 1):
        for tx in range(tx0, tx1 + 1):
            try:
                blob = _cached_get(DEM_URL.format(z=zoom, x=tx, y=ty), cache_dir, ".png")
                rgb = decode_png(blob).astype(np.float32)
                elev = (rgb[:, :, 0] * 256.0 + rgb[:, :, 1] + rgb[:, :, 2] / 256.0) - 32768.0
                ok += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  ! tile {zoom}/{tx}/{ty}: {exc}")
                elev = np.zeros((TILE, TILE), dtype=np.float32)
            mosaic[(ty - ty0) * TILE:(ty - ty0 + 1) * TILE,
                   (tx - tx0) * TILE:(tx - tx0 + 1) * TILE] = elev
    if ok == 0:
        raise RuntimeError("khong tai duoc tile DEM nao")

    bounds = {
        "zoom": zoom,
        "px_origin_x": x0 - tx0,
        "px_origin_y": y0 - ty0,
        "px_span_x": x1 - x0,
        "px_span_y": y1 - y0,
        "px_per_m": (2 ** zoom) * TILE / (2 * math.pi * EARTH_R * coslat),
        "north": north, "south": south, "west": west, "east": east,
        "coslat": coslat,
    }
    return mosaic, bounds


def sample_grid(mosaic: np.ndarray, bounds: dict, n: int) -> np.ndarray:
    """Lay mau song tuyen (bilinear) theo luoi n x n tren o vuong."""
    # vi tri pixel cua goc tren-trai, va buoc pixel giua hai nut luoi
    px0 = bounds["px_origin_x"] * TILE
    py0 = bounds["px_origin_y"] * TILE
    sx = bounds["px_span_x"] * TILE / (n - 1)
    sy = bounds["px_span_y"] * TILE / (n - 1)
    xs = px0 + sx * np.arange(n)
    ys = py0 + sy * np.arange(n)

    h, w = mosaic.shape
    xs = np.clip(xs, 0, w - 1.001)
    ys = np.clip(ys, 0, h - 1.001)
    x0 = np.floor(xs).astype(int)
    y0 = np.floor(ys).astype(int)
    fx = (xs - x0)[None, :]
    fy = (ys - y0)[:, None]
    a = mosaic[np.ix_(y0, x0)]
    b = mosaic[np.ix_(y0, x0 + 1)]
    c = mosaic[np.ix_(y0 + 1, x0)]
    d = mosaic[np.ix_(y0 + 1, x0 + 1)]
    top = a * (1 - fx) + b * fx
    bot = c * (1 - fx) + d * fx
    return (top * (1 - fy) + bot * fy).astype(np.float32)


# --------------------------------------------------------------------------
# Anh nen
# --------------------------------------------------------------------------

def fetch_imagery(lat: float, lng: float, half_m: float, tex: int,
                  cache_dir: str) -> bytes | None:
    coslat = math.cos(math.radians(lat))
    dlat = half_m / M_PER_DEG_LAT
    dlng = half_m / (M_PER_DEG_LNG_EQ * coslat)
    bbox = f"{lng - dlng},{lat - dlat},{lng + dlng},{lat + dlat}"
    size = min(tex, IMG_MAX)
    # Anh cang lon cang de timeout; ha dan kich thuoc thay vi bo anh.
    for s in (size, size // 2, 1024):
        if s < 256:
            break
        params = {"bbox": bbox, "bboxSR": "4326", "imageSR": "4326",
                  "size": f"{s},{s}", "format": "jpg", "f": "image"}
        url = IMG_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
        try:
            blob = _cached_get(url, cache_dir, ".jpg", retries=2, timeout=240)
            if blob[:2] != b"\xff\xd8":
                raise RuntimeError("khong phai JPEG")
            print(f"  anh nen {s}x{s} ({len(blob) / 1024 / 1024:.2f} MB)")
            return blob
        except Exception as exc:  # noqa: BLE001
            print(f"  ! anh {s}px that bai ({str(exc)[:60]}), thu lai nho hon")
    print("  ! khong lay duoc anh nen - GLB se chi co hinh khoi")
    return None


# --------------------------------------------------------------------------
# Dung mesh
# --------------------------------------------------------------------------

def median_filter(heights: np.ndarray, k: int) -> np.ndarray:
    """Loc trung vi - dat hon box blur: xoa blob tan cay, giu song nui."""
    if k < 3:
        return heights
    r = k // 2
    p = np.pad(heights, r, mode="edge")
    win = np.lib.stride_tricks.sliding_window_view(p, (k, k))
    return np.median(win, axis=(-2, -1)).astype(np.float32)


def smooth(heights: np.ndarray, passes: int) -> np.ndarray:
    """Loc hop 3x3 - DEM 30 m khong co chi tiet o muc 10 m, loc de bot nhieu noi suy."""
    h = heights.astype(np.float32)
    for _ in range(max(0, passes)):
        p = np.pad(h, 1, mode="edge")
        h = (p[:-2, :-2] + p[:-2, 1:-1] + p[:-2, 2:]
             + p[1:-1, :-2] + 4 * p[1:-1, 1:-1] + p[1:-1, 2:]
             + p[2:, :-2] + p[2:, 1:-1] + p[2:, 2:]) / 12.0
    return h


def build_mesh(heights: np.ndarray, size_m: float, z_scale: float,
               hole_m: float = 0.0):
    n = heights.shape[0]
    step = size_m / (n - 1)
    half = size_m / 2.0
    h = heights * z_scale
    base = float(h.min())
    h = h - base

    xs = np.linspace(-half, half, n, dtype=np.float32)
    zs = np.linspace(-half, half, n, dtype=np.float32)
    gx, gz = np.meshgrid(xs, zs, indexing="xy")  # gx[j,i]=X, gz[j,i]=Z

    pos = np.stack([gx, h.astype(np.float32), gz], axis=-1).reshape(-1, 3)

    # phap tuyen tu dao ham trung tam
    dhdz, dhdx = np.gradient(h, step)
    nrm = np.stack([-dhdx, np.ones_like(h), -dhdz], axis=-1).reshape(-1, 3)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)

    u = np.linspace(0.0, 1.0, n, dtype=np.float32)
    uv = np.stack(np.meshgrid(u, u, indexing="xy"), axis=-1).reshape(-1, 2)

    idx = []
    for j in range(n - 1):
        row = j * n
        nxt = (j + 1) * n
        for i in range(n - 1):
            if hole_m > 0.0:
                cx = -half + (i + 0.5) * step
                cz = -half + (j + 0.5) * step
                if cx * cx + cz * cz < hole_m * hole_m:
                    continue
            a, b = row + i, row + i + 1
            c, d = nxt + i, nxt + i + 1
            idx.extend((a, c, b, b, c, d))
    idx = np.asarray(idx, dtype=np.uint32)

    return pos, nrm, uv, idx, float(heights.min()), float(heights.max())


def write_glb(path: str, pos, nrm, uv, idx, jpeg: bytes | None, name: str) -> None:
    if len(pos) < 65536:
        idx = idx.astype(np.uint16)
        idx_ct = 5123
    else:
        idx_ct = 5125

    blobs, views, offset = [], [], 0
    for arr in (pos, nrm, uv):
        raw = arr.astype("<f4").tobytes()
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(raw),
                      "target": 34962})
        blobs.append(raw)
        offset += len(raw)
    raw_idx = idx.astype("<u2" if idx_ct == 5123 else "<u4").tobytes()
    views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(raw_idx),
                  "target": 34963})
    blobs.append(raw_idx)
    offset += len(raw_idx)

    img_view = None
    if jpeg:
        pad = (4 - offset % 4) % 4
        if pad:
            blobs.append(b"\x00" * pad)
            offset += pad
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(jpeg)})
        blobs.append(jpeg)
        img_view = len(views) - 1
        offset += len(jpeg)

    binary = b"".join(blobs)
    binary += b"\x00" * ((4 - len(binary) % 4) % 4)

    acc = [
        {"bufferView": 0, "componentType": 5126, "count": len(pos), "type": "VEC3",
         "min": [float(v) for v in pos.min(axis=0)],
         "max": [float(v) for v in pos.max(axis=0)]},
        {"bufferView": 1, "componentType": 5126, "count": len(nrm), "type": "VEC3"},
        {"bufferView": 2, "componentType": 5126, "count": len(uv), "type": "VEC2"},
        {"bufferView": 3, "componentType": idx_ct, "count": int(idx.size), "type": "SCALAR"},
    ]

    gltf = {
        "asset": {"version": "2.0", "generator": "heritage terrain-gen"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": name, "mesh": 0}],
        "meshes": [{"name": name, "primitives": [{
            "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
            "indices": 3, "material": 0, "mode": 4}]}],
        "materials": [{
            "name": "terrain",
            "doubleSided": False,
            "pbrMetallicRoughness": {
                "baseColorTexture": {"index": 0},
                "metallicFactor": 0.0, "roughnessFactor": 1.0}}],
        "textures": [{"sampler": 0, "source": 0}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987,
                      "wrapS": 33071, "wrapT": 33071}],
        "images": [{"mimeType": "image/jpeg", "bufferView": img_view}] if jpeg else [],
        "accessors": acc,
        "bufferViews": views,
        "buffers": [{"byteLength": len(binary)}],
    }
    if not jpeg:
        del gltf["textures"], gltf["samplers"]
        gltf["materials"][0]["pbrMetallicRoughness"] = {
            "baseColorFactor": [0.78, 0.71, 0.60, 1.0],
            "metallicFactor": 0.0, "roughnessFactor": 1.0}

    js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    js += b" " * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + 8 + len(binary)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<4sII", b"glTF", 2, total))
        fh.write(struct.pack("<I4s", len(js), b"JSON") + js)
        fh.write(struct.pack("<I4s", len(binary), b"BIN\x00") + binary)


def write_preview(path: str, heights: np.ndarray, tex: int = 900) -> None:
    """Hillshade nhanh de kiem tra hinh khoi truoc khi mo trong app."""
    n = heights.shape[0]
    step = max(1, n // tex)
    h = heights[::step, ::step]
    gy, gx = np.gradient(h.astype(np.float32))
    slope = np.pi / 2 - np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az, alt = math.radians(315), math.radians(45)
    shade = (np.sin(alt) * np.sin(slope)
             + np.cos(alt) * np.cos(slope) * np.cos(az - aspect))
    shade = np.clip(shade, 0, 1)
    hn = (h - h.min()) / max(1e-6, h.max() - h.min())
    rgb = np.stack([shade * (0.55 + 0.45 * hn)] * 3, axis=-1)
    rgb = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    with open(path, "wb") as fh:
        fh.write(encode_png_rgb(rgb))


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Sinh lop dia hinh GLB cho mot toa do.")
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lng", type=float, required=True)
    ap.add_argument("--size", type=float, default=2000, help="canh o vuong, met (mac dinh 2000)")
    ap.add_argument("--grid", type=int, default=192, help="so nut moi canh (mac dinh 192)")
    ap.add_argument("--tex", type=int, default=3000, help="canh texture px, toi da 3000")
    ap.add_argument("--z-scale", type=float, default=1.0, help="he so phong do cao")
    ap.add_argument("--smooth", type=int, default=2, help="so lan loc 3x3 (mac dinh 2)")
    ap.add_argument("--median", type=int, default=5,
                    help="canh cua so loc trung vi, 0 = tat (mac dinh 5)")
    ap.add_argument("--hole", type=float, default=0.0,
                    help="ban kinh khoet lo giua, met (de long lop gan vao)")
    ap.add_argument("--dem-zoom", type=int, default=None)
    ap.add_argument("--no-texture", action="store_true")
    ap.add_argument("--out", default="terrain.glb")
    ap.add_argument("--preview", default=None, help="ghi anh hillshade PNG de kiem tra")
    ap.add_argument("--cache", default=".cache/terrain")
    ap.add_argument("--name", default=None, help="ten node trong GLB")
    args = ap.parse_args()

    t0 = time.time()
    half = args.size / 2.0
    step = args.size / (args.grid - 1)
    print(f"[1/4] DEM {args.lat:.5f}, {args.lng:.5f} · {args.size:.0f} m")
    mosaic, bounds = fetch_dem(args.lat, args.lng, half, args.cache,
                               args.dem_zoom, target_mpp=step)

    print(f"[2/4] lay mau {args.grid}x{args.grid} (buoc {step:.1f} m)")
    heights = sample_grid(mosaic, bounds, args.grid)
    heights = median_filter(heights, args.median)
    heights = smooth(heights, args.smooth)
    print(f"  do cao {heights.min():.1f} .. {heights.max():.1f} m "
          f"(chenh {heights.max() - heights.min():.1f} m)")

    jpeg = None
    if not args.no_texture:
        print("[3/4] anh nen")
        jpeg = fetch_imagery(args.lat, args.lng, half, args.tex, args.cache)
    else:
        print("[3/4] bo qua anh nen")

    pos, nrm, uv, idx, lo, hi = build_mesh(heights, args.size, args.z_scale, args.hole)
    name = args.name or f"gcontext_{args.lat:.4f}_{args.lng:.4f}".replace(".", "").replace("-", "m")
    write_glb(args.out, pos, nrm, uv, idx, jpeg, name)
    size_mb = os.path.getsize(args.out) / 1024 / 1024
    print(f"[4/4] {args.out} · {len(pos)} dinh · {len(idx) // 3} tam giac · {size_mb:.2f} MB")
    print(f"  Y=0 tai cao do {lo:.1f} m · dinh cao {hi - lo:.1f} m so voi mat chuan")
    print(f"  node '{name}' · UV phang · 1 material · xong sau {time.time() - t0:.1f}s")

    if args.preview:
        write_preview(args.preview, heights)
        print(f"  preview: {args.preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
