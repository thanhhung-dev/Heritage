"""Doi pose camera lay tu trinh duyet thanh SQL cho bang `scene`.

Vong lap chinh (khong can Blender):
    1. Mo tour trong trinh duyet (dev), vao dung canh.
    2. Tam dung audio (bam nut pause) de timeline khong keo camera nua.
    3. Keo chuot toi goc mong muon.
    4. Console:  __tourCameraDump()
    5. Copy JSON tra ve, chay:
         python tools/camera-pose-sql.py --slug lang-tu-duc --scene 0 --pose-file dump.json
    6. Chay file .sql sinh ra.

`__tourCameraDump()` tra ve dang:
    { "camera": { "position": [x,y,z], "target": [x,y,z], "fov": 50, ... }, ... }

Cong cu chi lay `camera.position` va `camera.target` — cac truong khac bo qua. Cung
nhan dang rut gon {"position": [...], "target": [...]} hoac mang [x,y,z] roi rac.

Nhieu canh mot luc:
    python tools/camera-pose-sql.py --slug lang-tu-duc --batch poses.json --out out.sql
voi poses.json = [{"scene": 0, "role": "start", "position": [...], "target": [...]}, ...]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

COLUMNS = {
    "start": ("cam_start_pos", "cam_start_target"),
    "zoom": ("cam_zoom_pos", "cam_zoom_target"),
}


def numbers(value, digits: int) -> list[float] | None:
    """Nhan [x,y,z] hoac {x,y,z} (three.js Vector3) -> list 3 so."""
    if isinstance(value, dict):
        value = [value.get("x"), value.get("y"), value.get("z")]
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    try:
        out = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    if not all(item == item and abs(item) != float("inf") for item in out):
        return None
    return [0.0 if round(item, digits) == 0 else round(item, digits) for item in out]


def read_pose(payload) -> tuple[list[float], list[float]]:
    """Boc moi dang input ve (position, target)."""
    if isinstance(payload, list) and len(payload) == 3 and all(
        isinstance(item, (int, float)) for item in payload
    ):
        raise SystemExit("Chi co mot vector — can ca position va target.")
    camera = payload.get("camera") if isinstance(payload, dict) and "camera" in payload else payload
    if not isinstance(camera, dict):
        raise SystemExit("Khong doc duoc pose: can object co 'position' va 'target'.")
    position = numbers(camera.get("position"), 3)
    target = numbers(camera.get("target"), 3)
    if position is None or target is None:
        raise SystemExit(f"Thieu/toa do khong hop le: position={camera.get('position')} target={camera.get('target')}")
    return position, target


def sql_for(slug: str, scene: int, role: str, position: list[float], target: list[float]) -> str:
    pos_col, target_col = COLUMNS[role]
    pos = json.dumps(position, separators=(",", ":"))
    tgt = json.dumps(target, separators=(",", ":"))
    return (
        "update scene set\n"
        f"  {pos_col} = '{pos}'::jsonb,\n"
        f"  {target_col} = '{tgt}'::jsonb\n"
        f"where heritage_id = (select id from heritage where slug = '{slug}')\n"
        f"  and sequence = {scene};"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Pose camera -> SQL cho bang scene")
    parser.add_argument("--slug", required=True, help="slug heritage, vd lang-tu-duc")
    parser.add_argument("--scene", type=int, help="sequence cua canh, vd 0..4")
    parser.add_argument("--role", choices=("start", "zoom"), default="start", help="goc Start hay Zoom")
    parser.add_argument("--pose", help="chuoi JSON cua __tourCameraDump()")
    parser.add_argument("--pose-file", help="file JSON chua output cua __tourCameraDump()")
    parser.add_argument("--batch", help="file JSON: [{scene, role, position, target}, ...]")
    parser.add_argument("--out", help="ghi SQL ra file thay vi in ra man hinh")
    parser.add_argument("--dry-run", action="store_true", help="chi in toa do, khong sinh SQL")
    args = parser.parse_args()

    statements: list[str] = []
    if args.batch:
        items = json.load(open(args.batch, encoding="utf-8"))
        if not isinstance(items, list):
            raise SystemExit("--batch can mot mang JSON")
        for item in items:
            position, target = read_pose(item)
            role = item.get("role", "start")
            if role not in COLUMNS:
                raise SystemExit(f"role khong hop le: {role}")
            statements.append(sql_for(args.slug, int(item["scene"]), role, position, target))
    else:
        if args.scene is None:
            raise SystemExit("can --scene (hoac dung --batch)")
        if args.pose:
            payload = json.loads(args.pose)
        elif args.pose_file:
            payload = json.load(open(args.pose_file, encoding="utf-8"))
        else:
            payload = json.load(sys.stdin)
        position, target = read_pose(payload)
        if args.dry_run:
            print(f"position = {position}\ntarget   = {target}")
            return 0
        statements.append(sql_for(args.slug, args.scene, args.role, position, target))

    body = "begin;\n\n" + "\n\n".join(statements) + "\n\ncommit;\n"
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(body)
        print(f"[+] {len(statements)} cau lenh -> {args.out}")
    else:
        print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
