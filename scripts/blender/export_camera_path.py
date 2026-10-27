"""
Xuất QUỸ ĐẠO CAMERA ra GLB riêng (chỉ camera + animation, không mesh).

Dùng trong Blender: mở file .blend CÓ MODEL (quan trọng — xem ghi chú dưới),
sửa các hằng ở đầu file rồi bấm Run Script. Hoặc chạy headless:

    blender -b tuduc.blend -P scripts/blender/export_camera_path.py -- out/tuduc-s1.glb 12.5

Vì sao phải mở đúng file .blend có model: file path được nạp vào app ở CÙNG gốc
toạ độ với model. Nếu bạn dựng camera trong một file .blend rỗng khác, gốc và tỉ
lệ lệch ⇒ camera bay sai chỗ dù số trên màn hình Blender trông vẫn đúng.

Vì sao không export chung với model: model ~100 MB, mỗi lần chỉnh camera mà phải
export lại + upload lại R2 là vòng lặp không dùng được. File này chỉ vài chục KB.
"""
import os
import sys
import math

import bpy
from mathutils import Vector

# ─── Sửa ở đây ────────────────────────────────────────────────────────────────
CAMERA_NAME = ""            # "" = camera đang active của scene
TARGET_NAME = "CAM_Target"  # Empty làm điểm ngắm; "" = không tạo
NARRATION_SECONDS = 0.0     # > 0 ⇒ đặt frame_end = fps × số giây này
OUT_PATH = "//camera_path.glb"   # "//" = cùng thư mục với file .blend
# ──────────────────────────────────────────────────────────────────────────────

# Cho phép ghi đè bằng tham số dòng lệnh: -- <out_path> [narration_seconds]
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if argv:
    OUT_PATH = argv[0]
if len(argv) > 1:
    NARRATION_SECONDS = float(argv[1])


def log(message):
    print(f"[camera-path] {message}")


def pick_camera():
    if CAMERA_NAME:
        cam = bpy.data.objects.get(CAMERA_NAME)
        if cam is None or cam.type != "CAMERA":
            raise RuntimeError(f"Không thấy camera tên {CAMERA_NAME!r}")
        return cam
    cam = bpy.context.scene.camera
    if cam is None:
        raise RuntimeError("Scene chưa gán camera active — đặt CAMERA_NAME hoặc gán scene.camera")
    return cam


def ensure_target(camera):
    """Empty làm điểm ngắm. Có nó thì app quay quanh đúng tâm bạn chọn thay vì
    tự bắn tia vào model để đoán."""
    if not TARGET_NAME:
        return None
    obj = bpy.data.objects.get(TARGET_NAME)
    if obj is None:
        obj = bpy.data.objects.new(TARGET_NAME, None)
        obj.empty_display_type = "PLAIN_AXES"
        bpy.context.scene.collection.objects.link(obj)
        # Mặc định đặt ngay trước mặt camera 20 m, bạn kéo lại tuỳ ý.
        loc = camera.matrix_world.translation.copy()
        direction = camera.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
        obj.location = loc + direction * 20.0
        log(f"tạo {TARGET_NAME} tại {tuple(round(v, 2) for v in obj.location)} — nhớ keyframe nếu nó cần di chuyển")
    return obj


def action_info(obj):
    anim = obj.animation_data
    action = anim.action if anim else None
    if action is None:
        return None
    start, end = action.frame_range
    fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
    return {
        "name": action.name,
        "frames": (start, end),
        "seconds": (end - start) / fps if fps else 0.0,
    }


def main():
    scene = bpy.context.scene
    fps = scene.render.fps / scene.render.fps_base
    camera = pick_camera()

    if NARRATION_SECONDS > 0:
        scene.frame_start = 1
        scene.frame_end = max(2, round(1 + NARRATION_SECONDS * fps))
        log(f"frame range = 1..{scene.frame_end} @ {fps:g} fps ⇒ {NARRATION_SECONDS:g} s")

    info = action_info(camera)
    if info is None:
        raise RuntimeError(
            f"Camera {camera.name!r} chưa có Action nào. Đặt con trỏ vào camera, bấm I để "
            "keyframe Location + Rotation ít nhất 2 mốc, rồi chạy lại."
        )

    target = ensure_target(camera)

    # Chỉ chọn camera (+ target) ⇒ file ra không có mesh nào.
    bpy.ops.object.select_all(action="DESELECT")
    camera.select_set(True)
    if target:
        target.select_set(True)
    bpy.context.view_layer.objects.active = camera

    out = bpy.path.abspath(OUT_PATH)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    wanted = {
        "filepath": out,
        "export_format": "GLB",
        "use_selection": True,          # chỉ export thứ đang chọn
        "export_cameras": True,         # BẮT BUỘC: thiếu là không có node camera
        "export_animations": True,
        "export_animation_mode": "ACTIONS",   # mỗi Action ⇒ một clip, tên clip = tên Action
        "export_force_sampling": True,        # nướng từng frame ⇒ đường cong khớp tuyệt đối
        "export_frame_range": False,          # lấy đúng range của Action, không theo scene
        "export_yup": True,                   # +Y up: ĐỪNG tắt, app đọc hệ Y-up
        "export_apply": False,
        "export_extras": False,
        "export_materials": "NONE",
        "export_normals": False,
        "export_texcoords": False,
        "export_skins": False,
        "export_morph": False,
    }
    # Lọc theo đúng tham số operator của phiên bản Blender đang chạy: tên tham số
    # đổi giữa các bản, truyền thừa một cái là TypeError và không export gì cả.
    supported = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    kwargs = {key: value for key, value in wanted.items() if key in supported}
    dropped = sorted(set(wanted) - set(kwargs))
    if dropped:
        log(f"bỏ qua tham số không có ở bản Blender này: {', '.join(dropped)}")

    bpy.ops.export_scene.gltf(**kwargs)

    size_kb = os.path.getsize(out) / 1024 if os.path.exists(out) else 0
    lens = camera.data.lens
    yfov = 2 * math.degrees(math.atan(camera.data.sensor_width / (2 * lens)))
    log("─" * 62)
    log(f"file          : {out}  ({size_kb:.1f} KB)")
    log(f"camera        : {camera.name}  ·  lens {lens:.1f} mm ⇒ yfov ≈ {yfov:.1f}°")
    log(f"clip          : {info['name']}  ·  {info['frames'][0]:.0f}..{info['frames'][1]:.0f} frame"
        f"  ·  {info['seconds']:.2f} s")
    log(f"target node   : {target.name if target else 'không có (app sẽ tự bắn tia vào model)'}")
    log("─" * 62)
    if NARRATION_SECONDS > 0 and abs(info["seconds"] - NARRATION_SECONDS) > 0.5:
        log(f"CẢNH BÁO: clip dài {info['seconds']:.2f} s nhưng narration {NARRATION_SECONDS:.2f} s")
    log("Nạp lên R2 rồi điền (URL tuyệt đối):")
    log(f"  UPDATE scene SET camera_path_url = '<R2>/…/{os.path.basename(out)}' WHERE id = <scene_id>;")


if __name__ == "__main__":
    main()
