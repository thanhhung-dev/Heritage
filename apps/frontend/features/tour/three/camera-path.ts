import * as THREE from "three";
import type { GLTF } from "three/addons/loaders/GLTFLoader.js";

import { camLog, camWarn } from "./camera-debug";

/**
 * Quỹ đạo camera nạp từ một file GLB **chỉ chứa camera + animation clip**.
 *
 * Vì sao tách khỏi model chính: model photogrammetry của tour nặng ~100 MB, nên
 * mỗi lần chỉnh camera mà phải export lại model là vòng lặp không dùng được.
 * File path chỉ có vài chục KB, sửa/xuất lại trong vài giây, và không làm đổi
 * version của object trên CDN.
 *
 * Cách dùng: `sample(seconds)` đặt clip về đúng thời điểm đó rồi trả pose. Gọi
 * mỗi frame với đồng hồ audio ⇒ camera bám lời thuyết minh, seek/pause/tua đều
 * đúng vì thời gian là ĐẦU VÀO chứ không phải trạng thái tích luỹ.
 */

/** Tên node được coi là "điểm ngắm" đi kèm camera trong file path. */
const TARGET_NODE_NAMES = new Set([
  "cam_target",
  "camera_target",
  "cameratarget",
  "target",
  "look_at",
  "lookat",
  "aim",
  "focus",
]);

/** FOV dùng khi node quay phim không phải camera phối cảnh. */
const DEFAULT_FOV = 50;

export interface CameraPathPose {
  position: THREE.Vector3;
  /** Điểm OrbitControls quay quanh — luôn là một điểm thật, không bao giờ null. */
  target: THREE.Vector3;
  fov: number;
}

/** Nguồn của `target` — chỉ để chẩn đoán. */
export type CameraPathTargetSource = "node" | "ray" | "center" | "provisional";

export interface CameraPath {
  readonly url: string;
  /** Thời lượng clip (giây). Audio dài hơn thì camera đứng ở frame cuối. */
  readonly duration: number;
  readonly clipName: string;
  readonly cameraName: string;
  readonly targetSource: () => CameraPathTargetSource;
  /**
   * Pose tại `seconds` (đã kẹp vào `[0, duration]`).
   *
   * Trả `null` khi file không có camera/clip dùng được — nơi gọi còn lùi về preset.
   */
  sample(seconds: number): CameraPathPose | null;
  dispose(): void;
}

/** Tên node đã chuẩn hoá giống cách three.js đặt tên track (`PropertyBinding`). */
function trackNodeName(name: string) {
  return THREE.PropertyBinding.sanitizeNodeName(name).trim().toLowerCase();
}

/**
 * Chọn clip để chạy.
 *
 * Ưu tiên clip có tên nói về camera/quỹ đạo (file có thể lẫn clip khác), rồi tới
 * clip dài nhất — clip dài nhất gần như luôn là clip của camera chính.
 */
export function pickCameraClip(clips: THREE.AnimationClip[]): THREE.AnimationClip | null {
  if (clips.length === 0) return null;
  if (clips.length === 1) return clips[0];
  const named = clips.find((clip) => /cam|path|fly|orbit|dolly/i.test(clip.name));
  if (named) return named;
  return clips.reduce((longest, clip) => (clip.duration > longest.duration ? clip : longest));
}

/**
 * Chọn node đóng vai camera.
 *
 * Ưu tiên camera phối cảnh có tên xuất hiện trong track của clip — đó đúng là
 * node mà clip điều khiển. Không có thì lấy camera phối cảnh đầu tiên, rồi mới
 * tới một node thường có tên kiểu camera (trường hợp tác giả export một Empty
 * thay vì camera thật).
 */
export function pickCameraNode(
  gltf: GLTF,
  clip: THREE.AnimationClip,
): THREE.Object3D | null {
  const animated = new Set(
    clip.tracks.map((track) => trackNodeName(track.name.split(".")[0])),
  );
  const perspectives = gltf.cameras.filter(
    (item): item is THREE.PerspectiveCamera => item instanceof THREE.PerspectiveCamera,
  );
  const animatedCamera = perspectives.find((item) => animated.has(trackNodeName(item.name)));
  if (animatedCamera) return animatedCamera;
  if (perspectives[0]) return perspectives[0];

  let fallback: THREE.Object3D | null = null;
  gltf.scene.traverse((object) => {
    if (fallback) return;
    const name = trackNodeName(object.name);
    if (animated.has(name) && /cam/.test(name)) fallback = object;
  });
  return fallback;
}

/** Node "điểm ngắm" tuỳ chọn — có thì dùng luôn, chính xác hơn suy đoán. */
export function pickTargetNode(root: THREE.Object3D): THREE.Object3D | null {
  let found: THREE.Object3D | null = null;
  root.traverse((object) => {
    if (found || object === root) return;
    const name = object.name.trim().toLowerCase();
    if (TARGET_NODE_NAMES.has(name)) found = object;
  });
  return found;
}

/**
 * Dựng `CameraPath` từ GLTF đã nạp. Trả `null` khi file không dùng được — nơi
 * gọi phải lùi về preset chứ không được làm gãy cảnh.
 */
export function createCameraPath(
  gltf: GLTF,
  url: string,
  modelRoot: THREE.Object3D | null,
): CameraPath | null {
  const clip = pickCameraClip(gltf.animations);
  if (!clip) {
    camWarn("path", `${url} không có animation clip nào ⇒ bỏ qua quỹ đạo camera`);
    return null;
  }
  const cameraNode = pickCameraNode(gltf, clip);
  if (!cameraNode) {
    camWarn("path", `${url} không có node camera nào (clip ${JSON.stringify(clip.name)}) ⇒ bỏ qua`);
    return null;
  }

  const root = gltf.scene;
  const targetNode = pickTargetNode(root);
  const mixer = new THREE.AnimationMixer(root);
  const action = mixer.clipAction(clip);
  action.play();
  // KHÔNG `paused`: `sample()` tự đặt `action.time` rồi gọi `mixer.update(0)`.
  // Paused sẽ khiến `_updateTimeScale()` trả 0 và việc seek mất tác dụng.
  action.setEffectiveWeight(1);

  const duration = clip.duration;
  const scratchPosition = new THREE.Vector3();
  const scratchDirection = new THREE.Vector3();
  const scratchQuaternion = new THREE.Quaternion();
  const pose: CameraPathPose = {
    position: new THREE.Vector3(),
    target: new THREE.Vector3(),
    fov: DEFAULT_FOV,
  };

  /**
   * Khoảng cách tới điểm ngắm khi file KHÔNG kèm node target.
   *
   * OrbitControls cần một điểm thật để quay quanh; lấy `position + hướng` với
   * khoảng cách 1 m thì với model vài trăm mét mỗi lần kéo chuột là model văng
   * khỏi màn hình. Vì vậy bắn một tia từ camera vào model và lấy đúng chỗ nó
   * nhìn — cùng cách `tour-engine` đang làm cho camera nướng trong GLB.
   *
   * `null` = chưa chốt được (model chưa nạp xong) ⇒ dùng tạm 10 m và KHÔNG cache,
   * frame sau thử lại.
   */
  let lookDistance: number | null = null;
  let targetSource: CameraPathTargetSource = "provisional";
  const probe = new THREE.Raycaster();
  const box = new THREE.Box3();
  const center = new THREE.Vector3();

  const resolveDistance = (position: THREE.Vector3, direction: THREE.Vector3) => {
    if (lookDistance !== null) return lookDistance;
    const hasModel = !!modelRoot && modelRoot.children.length > 0;

    if (hasModel && modelRoot) {
      probe.set(position, direction);
      const hit = probe.intersectObject(modelRoot, true)[0];
      if (hit && hit.distance > 1e-3) {
        lookDistance = hit.distance;
        targetSource = "ray";
        camLog("path", `điểm ngắm theo tia chiếu · ${lookDistance.toFixed(1)} m`);
        return lookDistance;
      }
      // Tia trượt (camera đang hướng ra ngoài model): vẫn phải có một tâm quay
      // hợp lý, lấy khoảng cách tới tâm hộp bao của model.
      box.setFromObject(modelRoot);
      if (!box.isEmpty()) {
        lookDistance = Math.max(position.distanceTo(box.getCenter(center)), 1);
        targetSource = "center";
        camLog("path", `điểm ngắm theo tâm model · ${lookDistance.toFixed(1)} m`);
        return lookDistance;
      }
    }

    targetSource = "provisional";
    return 10;
  };

  return {
    url,
    duration,
    clipName: clip.name,
    cameraName: cameraNode.name,
    targetSource: () => (targetNode ? "node" : targetSource),
    sample(seconds: number) {
      const time = Number.isFinite(seconds)
        ? THREE.MathUtils.clamp(seconds, 0, duration)
        : 0;
      // Đặt thời gian trực tiếp rồi cập nhật với delta 0: clip được ĐÁNH GIÁ tại
      // `time`, không tích luỹ. Nhờ vậy seek, pause và phát lại đều cho cùng kết
      // quả — điều kiện bắt buộc để bám audio.
      action.time = time;
      mixer.update(0);
      // Mixer chỉ ghi vào `position/quaternion` của node, chưa tính ma trận thế
      // giới; không cập nhật thì `getWorldPosition` trả giá trị của frame trước.
      root.updateMatrixWorld(true);

      cameraNode.getWorldPosition(scratchPosition);
      cameraNode.getWorldQuaternion(scratchQuaternion);
      // `Object3D.getWorldDirection` trả +Z còn `Camera` trả −Z; tự dựng vector
      // để hai loại node cho cùng một nghĩa "phía trước".
      scratchDirection.set(0, 0, -1).applyQuaternion(scratchQuaternion).normalize();

      pose.position.copy(scratchPosition);
      if (targetNode) {
        targetNode.getWorldPosition(pose.target);
      } else {
        pose.target
          .copy(scratchPosition)
          .addScaledVector(scratchDirection, resolveDistance(scratchPosition, scratchDirection));
      }
      pose.fov =
        cameraNode instanceof THREE.PerspectiveCamera ? cameraNode.fov : DEFAULT_FOV;
      return pose;
    },
    dispose() {
      mixer.stopAllAction();
      mixer.uncacheRoot(root);
      camLog("path", `đóng ${url}`);
    },
  };
}
