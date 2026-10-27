import assert from "node:assert/strict";
import test from "node:test";
import * as THREE from "three";
import type { GLTF } from "three/addons/loaders/GLTFLoader.js";
import {
  createCameraPath,
  pickCameraClip,
  pickCameraNode,
} from "../features/tour/three/camera-path";

/**
 * File path thật là GLB do Blender xuất, nhưng thứ cần kiểm tra là PHÉP SEEK:
 * đặt `seconds` thì pose phải đúng bằng pose của clip tại thời điểm đó, không
 * phụ thuộc số lần gọi trước đó. Dựng GLTF tối thiểu là đủ để kiểm tra điều này.
 */
function makeCameraGLTF({
  clipName = "CameraPath",
  duration = 2,
  cameraName = "Cam_Path",
}: { clipName?: string; duration?: number; cameraName?: string } = {}): GLTF {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, 1.6, 0.1, 1000);
  camera.name = cameraName;
  scene.add(camera);

  const node = THREE.PropertyBinding.sanitizeNodeName(cameraName);
  const position = new THREE.VectorKeyframeTrack(
    `${node}.position`,
    [0, duration],
    [0, 0, 0, 10, 0, 0],
  );
  // Xoay 90° quanh Y ở cuối clip ⇒ hướng nhìn đổi từ −Z sang −X.
  const half = Math.SQRT1_2;
  const quaternion = new THREE.QuaternionKeyframeTrack(
    `${node}.quaternion`,
    [0, duration],
    [0, 0, 0, 1, 0, half, 0, half],
  );
  const clip = new THREE.AnimationClip(clipName, duration, [position, quaternion]);

  return { scene, cameras: [camera], animations: [clip] } as unknown as GLTF;
}

const near = (actual: THREE.Vector3, expected: [number, number, number], message: string) => {
  assert.ok(
    Math.abs(actual.x - expected[0]) < 0.01 &&
      Math.abs(actual.y - expected[1]) < 0.01 &&
      Math.abs(actual.z - expected[2]) < 0.01,
    `${message}: nhận ${actual.toArray().map((v) => v.toFixed(3)).join(", ")}`,
  );
};

test("camera path: seek đặt đúng vị trí của clip tại thời điểm yêu cầu", () => {
  const path = createCameraPath(makeCameraGLTF(), "cam.glb", null);
  assert.ok(path, "phải dựng được path từ GLB có camera + clip");
  assert.equal(path.duration, 2);

  near(path.sample(0)!.position, [0, 0, 0], "khung đầu");
  near(path.sample(1)!.position, [5, 0, 0], "giữa clip");
  near(path.sample(2)!.position, [10, 0, 0], "khung cuối");
});

test("camera path: seek là hàm thuần của thời gian, không tích luỹ", () => {
  const path = createCameraPath(makeCameraGLTF(), "cam.glb", null)!;
  // Nhảy lộn xộn rồi quay lại: cùng một `seconds` phải cho cùng một pose.
  path.sample(1.9);
  path.sample(0.2);
  const direct = path.sample(1)!.position.clone();
  path.sample(2);
  path.sample(0);
  near(path.sample(1)!.position, [direct.x, direct.y, direct.z], "seek lại lần hai");
  near(direct, [5, 0, 0], "vẫn đúng vị trí giữa clip");
});

test("camera path: audio dài hơn clip thì đứng ở frame cuối, không trôi", () => {
  const path = createCameraPath(makeCameraGLTF(), "cam.glb", null)!;
  near(path.sample(99)!.position, [10, 0, 0], "vượt thời lượng clip");
  near(path.sample(-5)!.position, [0, 0, 0], "thời gian âm");
});

test("camera path: điểm ngắm bám theo hướng nhìn của clip", () => {
  const path = createCameraPath(makeCameraGLTF(), "cam.glb", null)!;
  // Không có node target và không có model ⇒ target suy theo hướng nhìn.
  const start = path.sample(0)!;
  near(start.target, [0, 0, -start.position.distanceTo(start.target)], "nhìn theo −Z");
  const end = path.sample(2)!;
  assert.ok(end.target.x < end.position.x - 1, "cuối clip đã xoay sang −X");
  assert.ok(Math.abs(end.target.z - end.position.z) < 0.01, "không còn lệch theo Z");
});

test("camera path: file không có animation hoặc không có camera thì trả null", () => {
  const empty = makeCameraGLTF();
  empty.animations = [];
  assert.equal(createCameraPath(empty, "empty.glb", null), null);

  const noCamera = makeCameraGLTF();
  noCamera.cameras = [];
  // Node vẫn tên kiểu camera và vẫn được clip điều khiển ⇒ vẫn dùng được.
  assert.ok(createCameraPath(noCamera, "node-only.glb", null));
});

test("camera path: chọn clip theo tên trước, rồi tới clip dài nhất", () => {
  const short = new THREE.AnimationClip("CameraPath", 3, []);
  const long = new THREE.AnimationClip("Idle", 40, []);
  assert.equal(pickCameraClip([long, short])?.name, "CameraPath");

  const a = new THREE.AnimationClip("A", 2, []);
  const b = new THREE.AnimationClip("B", 9, []);
  assert.equal(pickCameraClip([a, b])?.name, "B");
  assert.equal(pickCameraClip([]), null);
});

test("camera path: chọn đúng node camera mà clip điều khiển", () => {
  const gltf = makeCameraGLTF();
  const clip = gltf.animations[0];
  assert.equal(pickCameraNode(gltf, clip)?.name, "Cam_Path");
});
