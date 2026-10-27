#!/usr/bin/env python3
"""
merge_glb.py - gan mot lop dia hinh (GLB terrain) vao GLB cong trinh co san.

Khong decode lai hinh hoc: chi noi them BIN chunk va danh lai index cua
bufferView / accessor / material / texture / image / sampler. Nho vay giu nguyen
Draco, KTX2, UV, material cua file goc.

  python tools/terrain-gen/merge_glb.py \
      --base tmp/TuDuckt.glb --terrain tmp/terrain-out/tuduc_near.glb \
      --out tmp/terrain-out/tuduc_merged.glb --auto

`--auto` tu tim: tam mat bang cua cong trinh (theo bbox world), muc dat chan
(phan vi 2% do cao dinh), va cao do cua terrain tai dung tam do.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys

import numpy as np
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COMP = {5126: "<f4", 5123: "<u2", 5125: "<u4", 5121: "<u1", 5122: "<i2"}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path: str):
    d = open(path, "rb").read()
    magic, ver, total = struct.unpack("<4sII", d[:12])
    if magic != b"glTF":
        raise ValueError(f"{path} khong phai GLB")
    clen, ctype = struct.unpack("<I4s", d[12:20])
    if ctype != b"JSON":
        raise ValueError("chunk dau khong phai JSON")
    js = json.loads(d[20:20 + clen].decode("utf-8"))
    off = 20 + clen
    bin_data = b""
    if off < len(d):
        blen, btype = struct.unpack("<I4s", d[off:off + 8])
        bin_data = d[off + 8:off + 8 + blen]
    return js, bin_data, total == len(d)


def accessor_array(js: dict, bin_data: bytes, idx: int) -> np.ndarray:
    a = js["accessors"][idx]
    if "bufferView" not in a:
        raise ValueError("accessor khong co bufferView (co the dang dung Draco)")
    bv = js["bufferViews"][a["bufferView"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    n = a["count"]
    nc = NCOMP[a["type"]]
    dt = np.dtype(COMP[a["componentType"]])
    stride = bv.get("byteStride") or nc * dt.itemsize
    if stride == nc * dt.itemsize:
        return np.frombuffer(bin_data, dtype=dt, count=n * nc, offset=off).reshape(n, nc)
    return np.stack([np.frombuffer(bin_data, dtype=dt, count=nc, offset=off + i * stride)
                     for i in range(n)])


def node_matrix(node: dict) -> np.ndarray:
    if "matrix" in node:
        return np.array(node["matrix"], dtype=float).reshape(4, 4).T
    t = np.array(node.get("translation", [0, 0, 0]), dtype=float)
    s = np.array(node.get("scale", [1, 1, 1]), dtype=float)
    q = np.array(node.get("rotation", [0, 0, 0, 1]), dtype=float)
    x, y, z, w = q
    r = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4)
    m[:3, :3] = r * s[None, :]
    m[:3, 3] = t
    return m


def world_matrices(js: dict) -> dict[int, np.ndarray]:
    out: dict[int, np.ndarray] = {}

    def walk(ni: int, parent: np.ndarray) -> None:
        m = parent @ node_matrix(js["nodes"][ni])
        out[ni] = m
        for ch in js["nodes"][ni].get("children", []):
            walk(ch, m)

    for root in js["scenes"][js.get("scene", 0)]["nodes"]:
        walk(root, np.eye(4))
    return out


def mesh_points(js: dict, bin_data: bytes, wm: dict[int, np.ndarray],
                decimate: int = 1) -> np.ndarray:
    chunks = []
    for ni, n in enumerate(js["nodes"]):
        if "mesh" not in n:
            continue
        m = wm.get(ni, np.eye(4))
        for p in js["meshes"][n["mesh"]]["primitives"]:
            pos = accessor_array(js, bin_data, p["attributes"]["POSITION"]).astype(np.float64)
            if decimate > 1:
                pos = pos[::decimate]
            w = pos @ m[:3, :3].T + m[:3, 3]
            chunks.append(w)
    return np.concatenate(chunks) if chunks else np.zeros((0, 3))


def merge(base_js, base_bin, ter_js, ter_bin, node_name, transform):
    js = json.loads(json.dumps(base_js))  # deep copy
    bv_off = len(js["bufferViews"])
    acc_off = len(js["accessors"])
    mat_off = len(js["materials"])
    tex_off = len(js.get("textures", []))
    img_off = len(js.get("images", []))
    smp_off = len(js.get("samplers", []))

    bin_pad = (-len(base_bin)) % 4
    bin_out = base_bin + b"\x00" * bin_pad
    base_len = len(bin_out)
    bin_out += ter_bin

    for bv in ter_js["bufferViews"]:
        nbv = dict(bv)
        nbv["byteOffset"] = bv.get("byteOffset", 0) + base_len
        js["bufferViews"].append(nbv)

    for a in ter_js["accessors"]:
        na = dict(a)
        if "bufferView" in a:
            na["bufferView"] = a["bufferView"] + bv_off
        js["accessors"].append(na)

    for m in ter_js.get("materials", []):
        nm = json.loads(json.dumps(m))
        pbr = nm.get("pbrMetallicRoughness", {})
        if "baseColorTexture" in pbr:
            pbr["baseColorTexture"]["index"] += tex_off
        if "metallicRoughnessTexture" in pbr:
            pbr["metallicRoughnessTexture"]["index"] += tex_off
        if "normalTexture" in nm:
            nm["normalTexture"]["index"] += tex_off
        js["materials"].append(nm)

    for t in ter_js.get("textures", []):
        nt = json.loads(json.dumps(t))
        if "sampler" in nt:
            nt["sampler"] = nt["sampler"] + smp_off
        if "source" in nt:
            nt["source"] = nt["source"] + img_off
        for ext in nt.get("extensions", {}).values():
            if "source" in ext:
                ext["source"] = ext["source"] + img_off
        js.setdefault("textures", []).append(nt)

    for im in ter_js.get("images", []):
        ni = json.loads(json.dumps(im))
        if "bufferView" in ni:
            ni["bufferView"] = ni["bufferView"] + bv_off
        js.setdefault("images", []).append(ni)

    for s in ter_js.get("samplers", []):
        js.setdefault("samplers", []).append(json.loads(json.dumps(s)))

    for mesh in ter_js["meshes"]:
        nm = json.loads(json.dumps(mesh))
        for p in nm["primitives"]:
            p["attributes"] = {k: v + acc_off for k, v in p["attributes"].items()}
            if "indices" in p:
                p["indices"] += acc_off
            if "material" in p:
                p["material"] += mat_off
        js["meshes"].append(nm)

    # them node cua terrain, roi boc tat ca trong mot group de dat transform
    mesh_map = {}
    for i, m in enumerate(ter_js["meshes"]):
        mesh_map[i] = len(base_js["meshes"]) + i
    first_new = len(js["nodes"])
    for ni, n in enumerate(ter_js["nodes"]):
        nn = json.loads(json.dumps(n))
        if "mesh" in nn:
            nn["mesh"] = mesh_map[nn["mesh"]]
        js["nodes"].append(nn)
    roots = [first_new + r for r in ter_js["scenes"][ter_js.get("scene", 0)]["nodes"]]

    group = {"name": node_name, "children": roots}
    group.update(transform)
    js["nodes"].append(group)
    js["scenes"][js.get("scene", 0)]["nodes"].append(len(js["nodes"]) - 1)

    used = js.setdefault("extensionsUsed", [])
    for e in ter_js.get("extensionsUsed", []):
        if e not in used:
            used.append(e)

    js["buffers"] = [{"byteLength": len(bin_out)}]
    return js, bin_out


def write_glb(path: str, js: dict, binary: bytes) -> int:
    binary = binary + b"\x00" * ((-len(binary)) % 4)
    js = dict(js)
    js["buffers"] = [{"byteLength": len(binary)}]
    payload = json.dumps(js, separators=(",", ":")).encode("utf-8")
    payload += b" " * ((-len(payload)) % 4)
    total = 12 + 8 + len(payload) + 8 + len(binary)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<4sII", b"glTF", 2, total))
        fh.write(struct.pack("<I4s", len(payload), b"JSON") + payload)
        fh.write(struct.pack("<I4s", len(binary), b"BIN\x00") + binary)
    return total


def main() -> int:
    ap = argparse.ArgumentParser(description="Gan terrain GLB vao GLB cong trinh.")
    ap.add_argument("--base", required=True, help="GLB cong trinh")
    ap.add_argument("--terrain", required=True, help="GLB terrain tu terrain_glb.py")
    ap.add_argument("--out", required=True)
    ap.add_argument("--auto", action="store_true",
                    help="tu canh theo bbox world cua cong trinh + cao do terrain tai tam")
    ap.add_argument("--x", type=float, default=0.0)
    ap.add_argument("--y", type=float, default=0.0)
    ap.add_argument("--z", type=float, default=0.0)
    ap.add_argument("--scale", type=float, default=1.0, help="he so phong terrain")
    ap.add_argument("--ground-percentile", type=float, default=2.0,
                    help="phan vi do cao coi la mat dat cua cong trinh")
    ap.add_argument("--ground-offset", type=float, default=-2.0,
                    help="ha terrain xuong bao nhieu met so voi mat dat (am = chim)")
    ap.add_argument("--name", default=None)
    args = ap.parse_args()

    print(f"[1/4] doc {os.path.basename(args.base)}")
    bjs, bbin, bok = read_glb(args.base)
    print(f"  JSON {len(bjs['nodes'])} node · {len(bjs['meshes'])} mesh · "
          f"{len(bjs['accessors'])} accessor · BIN {len(bbin)/1024/1024:.1f} MB · ok={bok}")

    tjs, tbin, tok = read_glb(args.terrain)
    tname = tjs["nodes"][0].get("name", "terrain")
    print(f"[2/4] doc {os.path.basename(args.terrain)} · node {tname!r} · ok={tok}")

    if args.auto:
        print("[3/4] tu canh")
        wm = world_matrices(bjs)
        pts = mesh_points(bjs, bbin, wm, decimate=7)
        mn, mx = pts.min(0), pts.max(0)
        cx, cz = (mn[0] + mx[0]) / 2, (mn[2] + mx[2]) / 2
        ground = float(np.percentile(pts[:, 1], args.ground_percentile))
        print(f"  bbox world X {mn[0]:.1f}..{mx[0]:.1f}  Y {mn[1]:.1f}..{mx[1]:.1f}  "
              f"Z {mn[2]:.1f}..{mx[2]:.1f}")
        print(f"  mat bang {mx[0]-mn[0]:.1f} x {mx[2]-mn[2]:.1f} m · "
              f"cao {mx[1]-mn[1]:.1f} m · {len(pts)} diem mau")

        tpos = accessor_array(tjs, tbin, tjs["meshes"][0]["primitives"][0]["attributes"]["POSITION"])
        n = int(round(len(tpos) ** 0.5))
        h_center = float(tpos[(n // 2) * n + n // 2, 1])
        print(f"  terrain {n}x{n} · cao do tai tam {h_center:.2f} m (so voi diem thap nhat)")
        ty = ground + args.ground_offset - h_center
        print(f"  dat terrain: x={cx:.2f} y={ty:.2f} z={cz:.2f} "
              f"(mat dat {ground:.2f} m, ha {args.ground_offset:+.1f} m)")
        tx, tyy, tz = cx, ty, cz
    else:
        print("[3/4] dung offset thu cong")
        tx, tyy, tz = args.x, args.y, args.z

    transform = {"translation": [tx, tyy, tz]}
    if args.scale != 1.0:
        transform["scale"] = [args.scale] * 3

    print("[4/4] noi BIN + danh lai index")
    mjs, mbin = merge(bjs, bbin, tjs, tbin, args.name or f"terrain_{tname}", transform)
    total = write_glb(args.out, mjs, mbin)
    print(f"  {args.out} · {total/1024/1024:.1f} MB · "
          f"{len(mjs['nodes'])} node · {len(mjs['meshes'])} mesh · "
          f"{len(mjs['accessors'])} accessor · {len(mjs['materials'])} material")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
