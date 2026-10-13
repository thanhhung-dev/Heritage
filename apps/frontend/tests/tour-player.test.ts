import assert from "node:assert/strict";
import test from "node:test";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { createCameraController } from "../features/tour/three/camera-controller";
import { createExploreController } from "../features/tour/three/explore-controller";
import { parseVtt } from "../features/tour/player/useCaptions";
import { createSceneHighlights, type TimedSceneHighlight } from "../features/tour/three/scene-highlights";
import type { ModelLoader } from "../features/tour/three/model-loader";

test("camera giữ đúng preset dưới target và ngoài khoảng fit, kể cả reset/exit Explore", () => {
  const document = new EventTarget();
  const element = Object.assign(new EventTarget(), {
    style: {}, ownerDocument: document, getRootNode: () => document,
  }) as unknown as HTMLElement;
  const camera = new THREE.PerspectiveCamera();
  const controls = new OrbitControls(camera, element);
  controls.maxPolarAngle = Math.PI / 2;
  controls.minDistance = 2;
  controls.maxDistance = 10;
  const controller = createCameraController(camera, controls);
  const explore = createExploreController(controller, controls);
  const position = [46.15, 7.356, -24.088];
  const target = [14.54, 8.074, -1.886];
  try {
    assert.equal(controller.applyPreset({ start_position: position, start_target: target } as Parameters<typeof controller.applyPreset>[0]), true);
    const assertPose = () => {
      controls.update();
      camera.position.toArray().forEach((value, index) => assert.ok(Math.abs(value - position[index]) < 1e-8));
      assert.deepEqual(controls.target.toArray(), target);
    };
    assertPose();
    explore.enter("standard");
    assertPose();
    explore.enter("free");
    camera.position.set(1, 20, 3);
    explore.reset();
    assertPose();
    explore.exit();
    assertPose();
  } finally {
    controls.dispose();
  }
});

test("bay camera tới preset: tiến dần rồi dừng đúng toạ độ, instant_move đặt ngay", () => {
  const document = new EventTarget();
  const element = Object.assign(new EventTarget(), {
    style: {}, ownerDocument: document, getRootNode: () => document,
  }) as unknown as HTMLElement;
  const camera = new THREE.PerspectiveCamera();
  const controls = new OrbitControls(camera, element);
  const controller = createCameraController(camera, controls);
  const preset = {
    start_position: [10, 20, 30], start_target: [1, 2, 3],
    zoom_position: [4, 5, 6], zoom_target: [0, 0, 0], node_name: null, instant_move: false,
  } as Parameters<typeof controller.flyToPreset>[0];
  try {
    // Bay 1 giây: chưa tới đích sau nửa chặng.
    assert.equal(controller.flyToPreset(preset, false, 1), true);
    assert.equal(controller.isFlying(), true);
    controller.update(0.5);
    assert.ok(camera.position.distanceTo(new THREE.Vector3(10, 20, 30)) > 1e-6);
    // Đi hết thời gian thì dừng đúng preset và hết bay.
    controller.update(0.5);
    assert.equal(controller.isFlying(), false);
    camera.position.toArray().forEach((value, index) => assert.ok(Math.abs(value - [10, 20, 30][index]) < 1e-8));
    assert.deepEqual(controls.target.toArray(), [1, 2, 3]);
    // duration 0 (instant_move) đặt ngay, không bay.
    assert.equal(controller.flyToPreset(preset, true, 0), true);
    assert.equal(controller.isFlying(), false);
    camera.position.toArray().forEach((value, index) => assert.ok(Math.abs(value - [4, 5, 6][index]) < 1e-6));
    controls.target.toArray().forEach((value, index) => assert.ok(Math.abs(value - [0, 0, 0][index]) < 1e-6));
  } finally {
    controls.dispose();
  }
});

test("preset nằm DƯỚI mặt phẳng ngang (polar > 90°) không bị maxPolarAngle kẹp", () => {
  const document = new EventTarget();
  const element = Object.assign(new EventTarget(), {
    style: {}, ownerDocument: document, getRootNode: () => document,
  }) as unknown as HTMLElement;
  const camera = new THREE.PerspectiveCamera();
  const controls = new OrbitControls(camera, element);
  // Mặc định engine: không cho camera xuống dưới target.
  controls.maxPolarAngle = Math.PI / 2;
  const controller = createCameraController(camera, controls);
  // Camera thấp hơn target ⇒ polar ~96°, đúng kiểu 4/7 preset trong tour.json.
  const position = [10, -2, 0];
  const target = [0, 0, 0];
  try {
    assert.equal(
      controller.applyPreset({ start_position: position, start_target: target } as Parameters<typeof controller.applyPreset>[0]),
      true,
    );
    // Mô phỏng vòng lặp render: mỗi frame controls.update() chạy SAU khi áp pose.
    for (let frame = 0; frame < 5; frame += 1) {
      controls.update();
      camera.position.toArray().forEach((value, index) => {
        assert.ok(Math.abs(value - position[index]) < 1e-8, `frame ${frame}: trục ${index} = ${value}, mong đợi ${position[index]}`);
      });
    }
  } finally {
    controls.dispose();
  }
});

test("tween tiến đều từng frame dù controls.update() chạy giữa các frame (không đứng im)", () => {
  const document = new EventTarget();
  const element = Object.assign(new EventTarget(), {
    style: {}, ownerDocument: document, getRootNode: () => document,
  }) as unknown as HTMLElement;
  const camera = new THREE.PerspectiveCamera();
  const controls = new OrbitControls(camera, element);
  controls.maxPolarAngle = Math.PI / 2;
  const controller = createCameraController(camera, controls);
  // Cả điểm đầu lẫn điểm cuối đều dưới mặt phẳng ngang.
  const preset = {
    start_position: [10, -2, 0], start_target: [0, 0, 0],
    zoom_position: [0, -6, 8], zoom_target: [0, 0, 0], node_name: null, instant_move: false,
  } as Parameters<typeof controller.flyToPreset>[0];
  try {
    assert.equal(controller.flyToPreset(preset, false, 1), true);
    const seen: number[] = [];
    // 12 frame × 0.1s = 1.2s > 1s ⇒ chuyến bay chắc chắn kết thúc (tránh sai số tích luỹ).
    for (let frame = 0; frame < 12; frame += 1) {
      controller.update(0.1);
      controls.update();
      seen.push(camera.position.y);
    }
    // Camera phải THỰC SỰ di chuyển: ít nhất một bước khác biệt đáng kể.
    const distinct = new Set(seen.map((value) => value.toFixed(4)));
    assert.ok(distinct.size > 3, `camera gần như đứng im, chỉ có ${distinct.size} vị trí khác nhau: ${seen.map((v) => v.toFixed(2)).join(", ")}`);
    assert.equal(controller.isFlying(), false);
    camera.position.toArray().forEach((value, index) => {
      assert.ok(Math.abs(value - [10, -2, 0][index]) < 1e-8, `dừng sai toạ độ ở trục ${index}`);
    });
  } finally {
    controls.dispose();
  }
});

test("camera bám toàn bộ audio 6s: tiến đều, pause giữ pose và seek nhảy đúng vị trí", () => {
  const document = new EventTarget();
  const element = Object.assign(new EventTarget(), {
    style: {}, ownerDocument: document, getRootNode: () => document,
  }) as unknown as HTMLElement;
  const camera = new THREE.PerspectiveCamera();
  const controls = new OrbitControls(camera, element);
  controls.maxPolarAngle = Math.PI / 2;
  const controller = createCameraController(camera, controls);
  const preset = {
    start_position: [0, 0, 100], start_target: [0, 0, 0],
    zoom_position: [0, 0, 10], zoom_target: [0, 0, 0],
    node_name: null, instant_move: false,
  } as Parameters<typeof controller.startTimeline>[0];
  // Clip 6s: mỗi 1.5s phải đi thêm đúng một phần tư quãng đường.
  try {
    assert.equal(controller.startTimeline(preset, 6), true);
    assert.equal(controller.hasTimeline(), true);
    // Vào cảnh: đặt ngay tại pose start.
    camera.position.toArray().forEach((value, index) => {
      assert.ok(Math.abs(value - [0, 0, 100][index]) < 1e-8, "chưa đặt tại pose start");
    });

    controller.updateTimeline(1.5);
    assert.ok(Math.abs(camera.position.z - 77.5) < 1e-8);
    controller.updateTimeline(3);
    const mid = camera.position.z;
    assert.ok(Math.abs(mid - 55) < 1e-8, `giữa audio z=${mid}, mong đợi 55`);
    controller.updateTimeline(3);
    assert.equal(camera.position.z, mid, "pause không được làm camera tiến tiếp");
    controller.updateTimeline(4.5);
    assert.ok(Math.abs(camera.position.z - 32.5) < 1e-8, "camera đến đích trước khi audio hết");

    // Audio kết thúc ⇒ tới hẳn pose zoom.
    controller.updateTimeline(6);
    assert.ok(Math.abs(camera.position.z - 10) < 1e-6, `hết đoạn bay z=${camera.position.z}, mong đợi 10`);
    // Quá đoạn bay ⇒ giữ nguyên ở pose zoom, không vượt quá.
    controller.updateTimeline(19);
    assert.ok(Math.abs(camera.position.z - 10) < 1e-6, "vượt đoạn bay mà camera còn chạy tiếp");

    // TUA VIDEO về giữa: camera phải nhảy tới đúng vị trí tương ứng (không chỉ tiến một chiều).
    controller.updateTimeline(3);
    assert.ok(Math.abs(camera.position.z - mid) < 1e-6, "seek ngược không đưa camera về đúng mốc cũ");
    // Tua về 0 ⇒ về lại pose start.
    controller.updateTimeline(0);
    assert.ok(Math.abs(camera.position.z - 100) < 1e-6, "seek về 0 không đặt lại pose start");
    // Audio ngắn không được bị kéo dài tới sàn 4s cũ.
    controller.startTimeline(preset, 2);
    controller.updateTimeline(2);
    assert.ok(Math.abs(camera.position.z - 10) < 1e-8);
  } finally {
    controls.dispose();
  }
});

test("metadata timeline đến khi đang chuyển cảnh không làm camera nhảy hoặc hủy chuyến bay", () => {
  const document = new EventTarget();
  const element = Object.assign(new EventTarget(), {
    style: {}, ownerDocument: document, getRootNode: () => document,
  }) as unknown as HTMLElement;
  const camera = new THREE.PerspectiveCamera();
  const controls = new OrbitControls(camera, element);
  const controller = createCameraController(camera, controls);
  const preset = {
    start_position: [12, 8, 40], start_target: [2, 3, 4],
    zoom_position: [6, 4, 10], zoom_target: [-2, 1, 3],
    node_name: null, instant_move: false,
  } as Parameters<typeof controller.startTimeline>[0];
  try {
    camera.position.set(-20, 15, 80);
    controller.flyToPreset(preset, false, 1.6);
    controller.update(0.4);
    const beforeMetadata = controller.snapshot();
    assert.equal(controller.startTimeline(preset, 6), true);
    assert.deepEqual(camera.position.toArray(), beforeMetadata.position.toArray());
    controller.updateTimeline(0);
    assert.deepEqual(camera.position.toArray(), beforeMetadata.position.toArray());
    controller.update(0.4);
    assert.ok(camera.position.distanceTo(beforeMetadata.position) > 1);
    controller.updateTimeline(1.5);
    assert.ok(camera.position.distanceTo(new THREE.Vector3(-4.75, 11, 56.25)) < 1e-8,
      "audio phát sớm phải hòa liên tục vào chuyến bay chuyển cảnh");
    controller.update(0.8);
    assert.ok(camera.position.distanceTo(new THREE.Vector3(12, 8, 40)) < 1e-8);
    // Audio pause ở mốc 1.5s: frame cuối chuyến bay vẫn phải về đúng pose này.
    controller.updateTimeline(1.5);
    assert.ok(camera.position.distanceTo(new THREE.Vector3(10.5, 7, 32.5)) < 1e-8);
    controller.updateTimeline(3);
    assert.ok(camera.position.distanceTo(new THREE.Vector3(9, 6, 25)) < 1e-8);
    assert.ok(controls.target.distanceTo(new THREE.Vector3(0, 2, 3.5)) < 1e-8);
  } finally {
    controls.dispose();
  }
});

test("startTimeline: không có pose zoom thì trả false; thiếu thời lượng thì giữ pose start", () => {
  const document = new EventTarget();
  const element = Object.assign(new EventTarget(), {
    style: {}, ownerDocument: document, getRootNode: () => document,
  }) as unknown as HTMLElement;
  const camera = new THREE.PerspectiveCamera();
  const controls = new OrbitControls(camera, element);
  controls.maxPolarAngle = Math.PI / 2;
  const controller = createCameraController(camera, controls);
  try {
    // Không có zoom_position ⇒ không thể bật timeline, nhưng vẫn đặt pose start.
    assert.equal(controller.startTimeline({
      start_position: [0, 0, 50], start_target: [0, 0, 0], node_name: null, instant_move: false,
    } as Parameters<typeof controller.startTimeline>[0], 12), false);
    assert.equal(controller.hasTimeline(), false);
    assert.ok(Math.abs(camera.position.z - 50) < 1e-8, "thiếu pose zoom mà không đặt pose start");

    // Có đủ pose nhưng chưa biết thời lượng (0) ⇒ đứng yên ở start.
    assert.equal(controller.startTimeline({
      start_position: [0, 0, 50], start_target: [0, 0, 0],
      zoom_position: [0, 0, 5], zoom_target: [0, 0, 0],
      node_name: null, instant_move: false,
    } as Parameters<typeof controller.startTimeline>[0], 0), false);
    // Vẫn ở pose start dù ta có tiến thời gian.
    controller.updateTimeline(10);
    assert.ok(Math.abs(camera.position.z - 50) < 1e-8, "thời lượng chưa biết mà camera đã chạy");
  } finally {
    controls.dispose();
  }
});

test("flyToPreset ghi đè timeline: bay chuyển cảnh không bị timeline kéo lại", () => {
  const document = new EventTarget();
  const element = Object.assign(new EventTarget(), {
    style: {}, ownerDocument: document, getRootNode: () => document,
  }) as unknown as HTMLElement;
  const camera = new THREE.PerspectiveCamera();
  const controls = new OrbitControls(camera, element);
  controls.maxPolarAngle = Math.PI / 2;
  const controller = createCameraController(camera, controls);
  const timelinePreset = {
    start_position: [0, 0, 100], start_target: [0, 0, 0],
    zoom_position: [0, 0, 10], zoom_target: [0, 0, 0],
    node_name: null, instant_move: false,
  } as Parameters<typeof controller.startTimeline>[0];
  try {
    controller.startTimeline(timelinePreset, 20);
    assert.equal(controller.hasTimeline(), true);
    // Tua: timeline có tác dụng.
    controller.updateTimeline(20);
    assert.ok(Math.abs(camera.position.z - 10) < 1e-6);

    // Bay tự do tới preset khác (mô phỏng focus marker) ⇒ timeline phải bị tắt.
    controller.flyToPreset({
      start_position: [0, 0, 300], start_target: [0, 0, 0],
      node_name: null, instant_move: false,
    } as Parameters<typeof controller.flyToPreset>[0], false, 0);
    assert.equal(controller.hasTimeline(), false, "flyToPreset không tắt timeline");
    // Timeline đã tắt ⇒ tiến thời gian không kéo camera đi nữa.
    controller.updateTimeline(20);
    assert.ok(Math.abs(camera.position.z - 300) < 1e-6, "timeline vẫn ghi đè sau khi bị thay bằng preset");
  } finally {
    controls.dispose();
  }
});

test("không có aliasing vector tạm: bay tới đúng toạ độ preset, lệch 0", () => {
  // Bug đã từng có: `allowPose` dùng chung một Vector3 tạm với tham số `position`
  // đang truyền vào, nên nó ghi đè chính giá trị cần áp ⇒ camera dừng sai toạ độ
  // (lệch đúng 10% quãng đường). Test này khoá hành vi đúng lại.
  const document = new EventTarget();
  const element = Object.assign(new EventTarget(), {
    style: {}, ownerDocument: document, getRootNode: () => document,
  }) as unknown as HTMLElement;
  const camera = new THREE.PerspectiveCamera();
  const controls = new OrbitControls(camera, element);
  const controller = createCameraController(camera, controls);
  const preset = {
    start_position: [12.5, 34.25, -7.75], start_target: [-3.5, 8.125, 19.5],
    zoom_position: [0, 0, 0], zoom_target: [0, 0, 0], node_name: null, instant_move: false,
  } as Parameters<typeof controller.flyToPreset>[0];
  try {
    controller.flyToPreset(preset, false, 1);
    controller.update(0.4);
    controller.update(0.4);
    controller.update(0.4);
    assert.equal(controller.isFlying(), false);
    // Sai số phải ở mức nhiễu số thực, KHÔNG được lệch theo tỉ lệ quãng đường.
    camera.position.toArray().forEach((value, index) => {
      assert.ok(
        Math.abs(value - [12.5, 34.25, -7.75][index]) < 1e-9,
        `trục ${index}: nhận ${value}, mong đợi ${[12.5, 34.25, -7.75][index]}`,
      );
    });
    controls.target.toArray().forEach((value, index) => {
      assert.ok(Math.abs(value - [-3.5, 8.125, 19.5][index]) < 1e-9, `target trục ${index} sai`);
    });
  } finally {
    controls.dispose();
  }
});

test("VTT đọc giờ/phút, cue ID, settings, nhiều dòng và bỏ cue sai", () => {
  assert.deepEqual(parseVtt(`WEBVTT\r\n\r\nNOTE ghi chú\r\nkhông phải cue\r\n\r\nintro\r\n00:01.250 --> 00:03.500 align:start\r\nDòng một\r\n<b>Dòng hai</b>\r\n\r\n01:02:03.004 --> 01:02:05.006\r\nCuối\r\n\r\n00:08.000 --> 00:07.000\r\nSai thứ tự`), [
    { start: 1.25, end: 3.5, text: "Dòng một\nDòng hai" },
    { start: 3723.004, end: 3725.006, text: "Cuối" },
  ]);
});

const highlight: TimedSceneHighlight = {
  id: 7, model_url: "/detail.glb", position: [2, 3, 4], rotation: [0, 0.2, 0], scale: [1, 2, 3],
  animation_type: "rotate", startSeconds: 0.5, endSeconds: 2.75,
};

test("highlight hiện trong [start,end), seek quay lại vẫn đúng animation", async () => {
  const scene = new THREE.Scene();
  const source = new THREE.Group();
  source.name = "detail";
  const loader = { load: async () => ({ scene: source }) } as unknown as ModelLoader;
  const controller = createSceneHighlights(scene, loader, () => {});
  await controller.set([highlight]);
  const model = scene.getObjectByName("detail")!;
  assert.deepEqual(model.position.toArray(), [2, 3, 4]);
  assert.deepEqual(model.scale.toArray(), [1, 2, 3]);
  controller.update(0.49);
  assert.equal(model.visible, false);
  controller.update(0.5);
  assert.equal(model.visible, true);
  controller.update(1.25);
  assert.ok(Math.abs(model.rotation.y - 0.95) < 1e-12);
  controller.update(2.75);
  assert.equal(model.visible, false);
  controller.update(0.5);
  assert.equal(model.visible, true);
  assert.equal(model.rotation.y, 0.2);
  controller.dispose();
});

test("model scene cũ tải trễ không xuất hiện sau khi thay scene", async () => {
  const scene = new THREE.Scene();
  const source = new THREE.Group();
  source.name = "old-detail";
  let finish!: (value: { scene: THREE.Group }) => void;
  const pending = new Promise<{ scene: THREE.Group }>((resolve) => { finish = resolve; });
  const loader = { load: () => pending } as unknown as ModelLoader;
  const controller = createSceneHighlights(scene, loader, () => {});
  const oldLoad = controller.set([highlight]);
  await controller.set([]);
  finish({ scene: source });
  await oldLoad;
  controller.update(1);
  assert.equal(scene.getObjectByName("old-detail"), undefined);
  controller.dispose();
});

test("highlight không có end_time giữ hiện, LoopRepeat seek theo thời gian narration", async () => {
  const scene = new THREE.Scene();
  const source = new THREE.Group();
  const animated = new THREE.Object3D();
  animated.name = "animated";
  source.add(animated);
  const clip = new THREE.AnimationClip("move", 2, [new THREE.NumberKeyframeTrack("animated.position[x]", [0, 2], [0, 8])]);
  const loader = { load: async () => ({ scene: source, animations: [clip] }) } as unknown as ModelLoader;
  const controller = createSceneHighlights(scene, loader, () => {});
  await controller.set([{ ...highlight, startSeconds: 2.5, endSeconds: null, animation_type: "LoopRepeat" }]);
  controller.update(3.25);
  assert.equal(scene.getObjectByName("animated")!.position.x, 3);
  controller.update(2.75);
  assert.equal(scene.getObjectByName("animated")!.position.x, 1);
  controller.update(100);
  const visible: string[] = [];
  scene.traverseVisible((object) => visible.push(object.name));
  assert.ok(visible.includes("animated"));
  assert.equal(scene.getObjectByName("animated")!.position.x, 6);
  assert.equal(controller.update(100), false);
  controller.dispose();
});
