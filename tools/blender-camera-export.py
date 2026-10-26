"""Xuat pose camera tu Blender ra toa do glTF de do vao bang `scene`.

Toa do camera cua tour 3D nam trong 4 cot JSONB cua bang `scene`
(`cam_start_pos`, `cam_start_target`, `cam_zoom_pos`, `cam_zoom_target`) va duoc
API tra thang ra client, KHONG qua bien doi nao. Vi vay con so trong Blender
phai duoc doi sang he truc cua glTF truoc khi ghi DB:

    Blender (Z-up, -Y la huong nhin mac dinh cua camera)
        -> glTF (Y-up, -Z la huong nhin)
        (gx, gy, gz) = (bx, bz, -by)

Day dung la phep doi ma glTF exporter cua Blender dung, nen toa do xuat ra khop
voi model sau khi export (don vi: met).

----------------------------------------------------------------------------
CACH CHAY
----------------------------------------------------------------------------
Headless (khuyen dung):

    blender -b kien-truc.blend -P tools/blender-camera-export.py -- \
        --out tmp/tuduc-cameras.json --sql tmp/tuduc-cameras.sql \
        --slug lang-tu-duc

Trong Blender: Scripting > Open > file nay > Run Script, roi xem System Console.

----------------------------------------------------------------------------
QUY UOC TEN
----------------------------------------------------------------------------
- `scene_sequence`: custom property (int) tren object camera, hoac so DAU TIEN
  trong ten (`Cam_S0`, `Cam_S1_zoom`...). Khong doc duoc thi lay
  `--sequence-start` + i.
- `camera_role`: custom property `start` | `zoom`. Khong co thi ten chua
  `zoom` => zoom, con lai => start.
- Diem ngam (target): uu tien object ten `<ten camera>_target`, roi custom
  property `target_node`, cuoi cung la `vi tri + huong nhin * --distance`.
  OrbitControls quay quanh target nen day la con so quan trong nhat.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys

import bpy  # type: ignore  # chi ton tai khi chay trong Blender
from mathutils import Vector  # type: ignore

FALLBACK_DISTANCE = 50.0


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser(description="Xuat pose camera Blender -> glTF")
    parser.add_argument("--out", default="cameras.json", help="file JSON ket qua")
    parser.add_argument("--sql", default=None, help="file .sql de chay len DB (tuy chon)")
    parser.add_argument("--slug", default=None, help="slug heritage, bat buoc khi xuat SQL")
    parser.add_argument(
        "--mode",
        choices=("coords", "node", "both"),
        default="coords",
        help="coords: ghi toa do (chay duoc ngay) · node: chi ghi camera_node_name "
             "(can camera nhung trong GLB) · both: ghi ca hai",
    )
    parser.add_argument(
        "--distance",
        type=float,
        default=FALLBACK_DISTANCE,
        help="khoang cach diem ngam khi khong co object target (met)",
    )
    parser.add_argument("--sequence-start", type=int, default=0, help="sequence cho camera khong doc duoc so")
    parser.add_argument("--precision", type=int, default=3, help="so chu so thap phan")
    return parser.parse_args(argv)


def to_gltf(vec: Vector) -> list[float]:
    """Blender Z-up -> glTF Y-up. Ap dung duoc cho ca diem va vector huong."""
    return [vec.x, vec.z, -vec.y]


def rounded(values: list[float], digits: int) -> list[float]:
    return [round(value, digits) for value in values]


def scene_sequence(obj, fallback: int) -> int:
    raw = obj.get("scene_sequence")
    if isinstance(raw, (int, float)):
        return int(raw)
    # Lay so DAU TIEN trong ten: "Cam_S1" va "Cam_S1_zoom" deu la canh 1.
    match = re.search(r"(\d+)", obj.name)
    return int(match.group(1)) if match else fallback


def camera_role(obj) -> str:
    raw = obj.get("camera_role")
    if isinstance(raw, str) and raw.lower() in {"start", "zoom"}:
        return raw.lower()
    return "zoom" if "zoom" in obj.name.lower() else "start"


def vertical_fov(obj) -> float:
    """yfov (radian) — goc mo theo chieu doc khung hinh, giong glTF exporter."""
    data = obj.data
    render = bpy.context.scene.render
    width, height = render.resolution_x or 1920, render.resolution_y or 1080
    aspect = height / width
    if data.sensor_fit == "VERTICAL":
        return data.angle_y
    if data.sensor_fit == "HORIZONTAL":
        return 2 * math.atan(math.tan(data.angle_x / 2) * aspect)
    # AUTO: sensor bam canh dai
    if width >= height:
        return 2 * math.atan(math.tan(data.angle_x / 2) * aspect)
    return data.angle_y


def find_object(name: str):
    wanted = name.strip().lower()
    for candidate in bpy.data.objects:
        if candidate.name.strip().lower() == wanted:
            return candidate
    return None


def target_point(obj, position: Vector, forward: Vector, distance: float):
    """Diem ngam + nguon goc cua no (de biet vi sao ra con so do)."""
    named = find_object(f"{obj.name}_target")
    if named is None:
        declared = obj.get("target_node")
        if isinstance(declared, str):
            named = find_object(declared)
    if named is not None:
        return named.matrix_world.to_translation(), f"node:{named.name}"
    return position + forward * distance, f"forward*{distance:g}m"


def main() -> int:
    args = parse_args()
    cameras = [item for item in bpy.data.objects if item.type == "CAMERA"]
    if not cameras:
        print("[!] Khong co camera nao trong file .blend", file=sys.stderr)
        return 1

    records = []
    for index, obj in enumerate(sorted(cameras, key=lambda item: item.name)):
        world = obj.matrix_world
        position = world.to_translation()
        rotation = world.to_quaternion()
        # Camera nhin doc truc -Z cua chinh no (ca o Blender lan glTF).
        forward = -(rotation @ Vector((0.0, 0.0, 1.0)))
        up = rotation @ Vector((0.0, 1.0, 0.0))
        aim, aim_source = target_point(obj, position, forward, args.distance)
        records.append(
            {
                "scene_sequence": scene_sequence(obj, args.sequence_start + index),
                "role": camera_role(obj),
                "node_name": obj.name,
                "position": rounded(to_gltf(position), args.precision),
                "target": rounded(to_gltf(aim), args.precision),
                "up": rounded(to_gltf(up), args.precision),
                "fov_y_deg": round(math.degrees(vertical_fov(obj)), 2),
                "lens_mm": round(obj.data.lens, 2),
                "target_source": aim_source,
            }
        )

    payload = {
        "unit": "metre",
        "up": "Y",
        "note": "Toa do trong he glTF, dung ngay cho cam_start_pos / cam_start_target.",
        "cameras": records,
    }

    out_path = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    print(f"[+] {len(records)} camera -> {out_path}")
    for record in records:
        print(
            f"    scene {record['scene_sequence']:>2} · {record['role']:<5} · "
            f"{record['node_name']:<20} pos={record['position']} target={record['target']} "
            f"({record['target_source']})"
        )

    if args.sql:
        if not args.slug:
            print("[!] --sql can --slug", file=sys.stderr)
            return 2
        lines = [
            "-- Sinh boi tools/blender-camera-export.py",
            f"-- heritage: {args.slug}",
            "begin;",
        ]
        for record in records:
            position = json.dumps(record["position"], separators=(",", ":"))
            target = json.dumps(record["target"], separators=(",", ":"))
            sets = []
            if args.mode in {"coords", "both"}:
                prefix = "cam_zoom" if record["role"] == "zoom" else "cam_start"
                sets.append(f"  {prefix}_pos = '{position}'::jsonb")
                sets.append(f"  {prefix}_target = '{target}'::jsonb")
            if args.mode in {"node", "both"}:
                sets.append(f"  camera_node_name = '{record['node_name']}'")
            lines.append(
                "update scene set\n" + ",\n".join(sets) + "\n"
                f"where heritage_id = (select id from heritage where slug = '{args.slug}')\n"
                f"  and sequence = {record['scene_sequence']};"
            )
        lines.append("commit;")
        sql_path = os.path.abspath(args.sql)
        os.makedirs(os.path.dirname(sql_path) or ".", exist_ok=True)
        with open(sql_path, "w", encoding="utf-8") as handle:
            handle.write("\n\n".join(lines) + "\n")
        print(f"[+] SQL -> {sql_path} (mode={args.mode})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
