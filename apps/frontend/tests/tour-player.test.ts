import assert from "node:assert/strict";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { createCameraController } from "../features/tour/three/camera-controller";
import { shouldEvaluateHover } from "../features/tour/three/tour-engine";
import { createExploreController } from "../features/tour/three/explore-controller";
import {
  clampPointToExploreArea,
  parseExploreArea,
} from "../features/tour/three/explore-area";
import {
  createWalkInput,
  DRAG_RADIUS,
  INPUT_DEAD_ZONE,
  WALK_SPEED,
} from "../features/tour/three/walk-controls";
import { parseVtt } from "../features/tour/player/useCaptions";
import { createSceneHighlights, type TimedSceneHighlight } from "../features/tour/three/scene-highlights";
import { createInteractiveHighlights } from "../features/tour/three/interactive-highlights";
import type { ModelLoader } from "../features/tour/three/model-loader";
import { HeritageTourContext } from "../context/heritage-tour";
import { useTourPlayer } from "../features/tour/player/useTourPlayer";
import { TEST_TOUR } from "../features/tour/tour-data";
import { interactiveUrl, isInteractivePath, sceneUrl } from "../lib/tour-routes";
import type { ExploreArea, HeritageScene } from "../types/heritage";

test("lens badge chọn đúng ID sau khi camera quay và không chọn khi ẩn hoặc thay scene", () => {
  const originalDocument = globalThis.document;
  // Canvas2D chỉ tạo texture; raycast không cần GPU. Render thật kiểm tra bằng Chrome.
  const context = {
    createRadialGradient: () => ({ addColorStop() {} }),
    fillRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {}, fillText() {},
  };
  globalThis.document = { createElement: () => ({ width: 256, height: 256, getContext: () => context }) } as unknown as Document;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera();
  const highlights = createInteractiveHighlights(scene);
  let selected: number | null = null;
  highlights.subscribe((item) => { selected = item?.id ?? null; });
  const base = TEST_TOUR.payload.scenes[1].interactive[0].highlights[0];
  try {
    highlights.set([
      { ...base, id: 987, sort_order: 2, lens_pos: [0, 3, 0], lens_scale: [20, 20, 20] },
      { ...base, id: 901, sort_order: 1, lens_pos: [0, 0, 0], lens_scale: [20, 20, 20] },
    ]);
    camera.position.set(5, 0, 0);
    camera.lookAt(0, 0, 0);
    highlights.show(true);
    highlights.update(camera);
    scene.updateMatrixWorld(true);
    const ray = new THREE.Raycaster(new THREE.Vector3(5, 0.2, 0.1), new THREE.Vector3(-1, 0, 0));
    highlights.pick(ray);
    assert.equal(selected, 901);
    highlights.select(null);
    highlights.pick(new THREE.Raycaster(new THREE.Vector3(5, 0.9, 0.9), new THREE.Vector3(-1, 0, 0)));
    assert.equal(selected, null);
    highlights.show(false);
    highlights.select(null);
    highlights.pick(ray);
    assert.equal(selected, null);
    highlights.set([{ ...base, id: 432, lens_pos: [0, 0, 0], lens_scale: [20, 20, 20] }]);
    highlights.show(true);
    camera.position.set(0, 0, -5);
    camera.lookAt(0, 0, 0);
    highlights.update(camera);
    scene.updateMatrixWorld(true);
    highlights.pick(new THREE.Raycaster(new THREE.Vector3(0.1, 0.2, -5), new THREE.Vector3(0, 0, 1)));
    assert.equal(selected, 432);
  } finally {
    highlights.dispose();
    globalThis.document = originalDocument;
  }
});

test("mở panel điểm ⇒ TẤT CẢ lens badge thu về 0, không chỉ badge vừa bấm", () => {
  const originalDocument = globalThis.document;
  const context = {
    createRadialGradient: () => ({ addColorStop() {} }),
    fillRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {}, fillText() {},
  };
  globalThis.document = { createElement: () => ({ width: 256, height: 256, getContext: () => context }) } as unknown as Document;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera();
  const highlights = createInteractiveHighlights(scene);
  const base = TEST_TOUR.payload.scenes[1].interactive[0].highlights[0];
  /** Tỉ lệ hiện tại của marker, đọc thẳng từ scene graph. */
  const scaleOf = (id: number) => {
    const marker = scene.getObjectByName(`hotspot_${id}`)?.children[0];
    assert.ok(marker, `thiếu marker hotspot_${id}`);
    return marker.scale.x;
  };
  const settle = (frames = 240) => {
    let animating = true;
    for (let i = 0; i < frames && animating; i += 1) animating = highlights.update(camera, 1 / 60);
    return animating;
  };
  const close = (actual: number, expected: number) =>
    assert.ok(Math.abs(actual - expected) < 1e-3, `mong ${expected}, nhận ${actual}`);
  try {
    highlights.set([
      { ...base, id: 11, sort_order: 1, lens_pos: [0, 0, 0], lens_scale: [1, 1, 1] },
      { ...base, id: 22, sort_order: 2, lens_pos: [0, 3, 0], lens_scale: [2, 2, 2] },
      { ...base, id: 33, sort_order: 3, lens_pos: [0, -3, 0], lens_scale: [3, 3, 3] },
    ]);
    highlights.show(true);
    assert.equal(settle(), false, "chưa chọn gì thì không có animation");
    close(scaleOf(11), 1);
    close(scaleOf(22), 2);
    close(scaleOf(33), 3);

    // Chọn badge 22: cả ba phải cùng teo, kể cả hai badge không liên quan.
    highlights.select(22);
    assert.equal(settle(), false, "badge phải dừng animation sau khi thu hết cỡ");
    close(scaleOf(11), 0);
    close(scaleOf(22), 0);
    close(scaleOf(33), 0);

    // Đóng panel: mọi badge phình lại đúng tỉ lệ gốc, không dính HOVER_SCALE.
    highlights.select(null);
    settle();
    close(scaleOf(11), 1);
    close(scaleOf(22), 2);
    close(scaleOf(33), 3);
  } finally {
    highlights.dispose();
    globalThis.document = originalDocument;
  }
});

test("Dive Deeper lấy khu vực, điểm và mode từ đúng cảnh của tour JSON", () => {
  let result: {
    id: number | null;
    mode: string;
    highlights: number[];
    area: ExploreArea | null;
    title: string | null;
  } | null = null;
  function Probe() {
    const player = useTourPlayer();
    result = {
      id: player.interactive?.id ?? null,
      mode: player.initialExploreMode,
      highlights: player.interactive?.highlights.map((item) => item.id) ?? [],
      area: player.exploreArea,
      title: player.exploreTitle,
    };
    return null;
  }
  function readScene(key: string, override?: HeritageScene) {
    const currentScene = override ?? [TEST_TOUR.payload.overview, ...TEST_TOUR.payload.scenes].find((scene) => scene?.slug === key) ?? null;
    renderToStaticMarkup(createElement(HeritageTourContext.Provider, { value: {
      payload: TEST_TOUR.payload, heritageSlug: "tapestry-test", currentSceneKey: key,
      currentScene, status: "ready", error: null, isModelReady: true,
      modelError: null,
      engine: null, scenePlayback: TEST_TOUR.playback[key],
    } }, createElement(Probe)));
    return result;
  }
  assert.deepEqual(readScene("s0"), { id: null, mode: "standard", highlights: [], area: null, title: null });
  const standard = readScene("s2");
  assert.equal(standard?.id, 332);
  assert.equal(standard?.mode, "standard");
  assert.deepEqual(standard?.highlights, [639, 640, 651]);
  // Cảnh không phải chế độ đi bộ ⇒ không có vùng kẹp, không có tiêu đề.
  assert.equal(standard?.area, null);
  assert.equal(standard?.title, null);
  // `free_explore` = đi bộ dưới đất, KHÔNG phải orbit tự do.
  const walk = readScene("s6");
  assert.equal(walk?.id, 428);
  assert.equal(walk?.mode, "walk");
  assert.deepEqual(walk?.highlights, []);
  assert.deepEqual(walk?.area?.extents, [21.64741446885839, 5.202717165968831, 18.27377018855391]);
  assert.deepEqual(walk?.area?.center, [11.64311165921454, 2.539100054773748, -2.11787469883124]);
  // Tiêu đề chỉ có nghĩa khi ĐANG ở trong chế độ ⇒ không `/int` thì phải là null.
  assert.equal(walk?.title, null);
  assert.deepEqual(readScene("s7"), { id: null, mode: "standard", highlights: [], area: null, title: null });
  // Cùng scene key nhưng thay dữ liệu: không được special-case ID hoặc mode.
  const scene = TEST_TOUR.payload.scenes[1];
  const area = scene.interactive[0];
  const overridden = readScene("s2", { ...scene, interactive: [{ ...area, id: 901, mode: "free",
    highlights: [{ ...area.highlights[0], id: 987 }],
  }] });
  assert.equal(overridden?.id, 901);
  assert.equal(overridden?.mode, "free");
  assert.deepEqual(overridden?.highlights, [987]);
});

test("chế độ điểm tương tác suy ra từ URL /int, không giữ state riêng", () => {
  let result: {
    exploreMode: string | null;
    initialExploreMode: string;
    title: string | null;
    description: string | null;
  } | null = null;
  function Probe({ interactiveRoute }: { interactiveRoute: boolean }) {
    const player = useTourPlayer({ interactiveRoute });
    result = {
      exploreMode: player.exploreMode,
      initialExploreMode: player.initialExploreMode,
      title: player.exploreTitle,
      description: player.exploreDescription,
    };
    return null;
  }
  function readScene(key: string, interactiveRoute: boolean) {
    const currentScene = [TEST_TOUR.payload.overview, ...TEST_TOUR.payload.scenes].find((scene) => scene?.slug === key) ?? null;
    renderToStaticMarkup(createElement(HeritageTourContext.Provider, { value: {
      payload: TEST_TOUR.payload, heritageSlug: "tapestry-test", currentSceneKey: key,
      currentScene, status: "ready", error: null, isModelReady: true,
      modelError: null,
      engine: null, scenePlayback: TEST_TOUR.playback[key],
    } }, createElement(Probe, { interactiveRoute })));
    return result;
  }
  // Không có `/int` thì không bao giờ ở chế độ điểm tương tác, kể cả cảnh có dữ liệu.
  assert.deepEqual(readScene("s2", false), { exploreMode: null, initialExploreMode: "standard", title: null, description: null });
  // Có `/int` ⇒ mode lấy từ chính dữ liệu cảnh, không hard-code.
  assert.deepEqual(readScene("s2", true), { exploreMode: "standard", initialExploreMode: "standard", title: null, description: null });
  assert.deepEqual(readScene("s6", true), {
    exploreMode: "walk", initialExploreMode: "walk",
    title: "Explore the Forecourt",
    description: TEST_TOUR.playback.s6.exploreDescription,
  });
  // Cảnh không có `interactive` ⇒ `/int` cũng không mở được chế độ nào.
  assert.deepEqual(readScene("s0", true), { exploreMode: null, initialExploreMode: "standard", title: null, description: null });
});

test("nhận diện route /int theo cấu trúc path, không nhầm cảnh tên 'int'", () => {
  assert.equal(isInteractivePath("/content/petra/s2/int"), true);
  assert.equal(isInteractivePath("/content/petra/s2"), false);
  assert.equal(isInteractivePath("/content/petra"), false);
  assert.equal(isInteractivePath("/content/petra/s2/int/"), true);
  // Cảnh có sceneKey đúng bằng "int": chỉ 3 đoạn ⇒ KHÔNG phải route điểm tương tác.
  assert.equal(isInteractivePath("/content/petra/int"), false);
  assert.equal(isInteractivePath("/admin/int"), false);
  assert.equal(isInteractivePath(null), false);
  assert.equal(interactiveUrl("petra", "s2"), "/content/petra/s2/int");
  assert.equal(sceneUrl("petra", "s2"), "/content/petra/s2");
});

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

test("thoát Explore bay về góc trước đó, không nhảy và có thể hủy khi đổi cảnh", () => {
  const document = new EventTarget();
  const element = Object.assign(new EventTarget(), {
    style: {}, ownerDocument: document, getRootNode: () => document,
  }) as unknown as HTMLElement;
  const camera = new THREE.PerspectiveCamera();
  const controls = new OrbitControls(camera, element);
  const controller = createCameraController(camera, controls);
  const explore = createExploreController(controller, controls);
  const preset = { start_position: [19, 12, -7], start_target: [2, 3, -1] } as Parameters<typeof controller.applyPreset>[0];
  try {
    controller.applyPreset(preset);
    camera.up.set(0, 0, 1);
    explore.enter("standard");
    controller.applyPreset({ ...preset, start_position: [-5, 6, 11], start_target: [-1, 2, 4] });
    explore.exit(1.2);
    assert.deepEqual(camera.position.toArray(), [-5, 6, 11]);
    controller.update(0.6);
    assert.ok(camera.position.distanceTo(new THREE.Vector3(7, 9, 2)) < 1e-8);
    assert.ok(controls.target.distanceTo(new THREE.Vector3(0.5, 2.5, 1.5)) < 1e-8);
    assert.ok(camera.up.distanceTo(new THREE.Vector3(0, 0.5, 0.5)) < 1e-8);
    controller.update(0.6);
    assert.ok(camera.position.distanceTo(new THREE.Vector3(19, 12, -7)) < 1e-8);
    assert.ok(controls.target.distanceTo(new THREE.Vector3(2, 3, -1)) < 1e-8);
    assert.deepEqual(camera.up.toArray(), [0, 0, 1]);
    explore.enter("free");
    controller.applyPreset({ ...preset, start_position: [-5, 6, 11] });
    explore.exit(1.2);
    controller.update(0.2);
    const stopped = controller.snapshot();
    controller.stopTimeline();
    controller.update(2);
    assert.ok(camera.position.distanceTo(stopped.position) < 1e-8);
  } finally {
    controls.dispose();
  }
});

test("camera focus tới đúng preset dù orbit còn quán tính damping", () => {
  const document = new EventTarget();
  const element = Object.assign(new EventTarget(), {
    style: {}, ownerDocument: document, getRootNode: () => document,
  }) as unknown as HTMLElement;
  const camera = new THREE.PerspectiveCamera();
  const controls = new OrbitControls(camera, element);
  controls.enableDamping = true;
  const controller = createCameraController(camera, controls);
  const preset = { start_position: [19, 12, -7], start_target: [2, 3, -1] } as Parameters<typeof controller.applyPreset>[0];
  try {
    controller.applyPreset(preset);
    controls.autoRotate = true;
    controls.autoRotateSpeed = 8;
    controls.update(0.1);
    controls.autoRotate = false;
    controller.flyToPreset(preset, false, 1.2);
    controller.update(1.2);
    controls.update();
    assert.ok(camera.position.distanceTo(new THREE.Vector3(19, 12, -7)) < 1e-8);
    assert.ok(controls.target.distanceTo(new THREE.Vector3(2, 3, -1)) < 1e-8);
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
    controller.updateTimeline(1.5);
    assert.ok(camera.position.distanceTo(beforeMetadata.position) < 1e-8,
      "metadata đến khi audio đã phát không được làm camera nhảy ở frame kế tiếp");
    controller.updateTimeline(0);
    assert.deepEqual(camera.position.toArray(), beforeMetadata.position.toArray());
    controller.update(0.4);
    assert.ok(camera.position.distanceTo(beforeMetadata.position) > 1);
    controller.updateTimeline(1.5);
    assert.ok(camera.position.distanceTo(beforeMetadata.position) > 1,
      "audio phát sớm phải hòa vào chuyến bay chuyển cảnh");
    controller.update(0.8);
    assert.ok(camera.position.distanceTo(new THREE.Vector3(12, 8, 40)) < 1e-8);
    // Audio pause ở mốc 1.5s: frame cuối chuyến bay vẫn phải về đúng pose này.
    controller.updateTimeline(1.5);
    assert.ok(camera.position.distanceTo(new THREE.Vector3(10.5, 7, 32.5)) < 1e-8);
    controller.updateTimeline(3);
    assert.ok(camera.position.distanceTo(new THREE.Vector3(9, 6, 25)) < 1e-8);
    assert.ok(controls.target.distanceTo(new THREE.Vector3(0, 2, 3.5)) < 1e-8);
    controller.flyToPreset(preset, false, 1.6);
    controller.update(0.2);
    controller.stopTimeline();
    const stopped = controller.snapshot();
    controller.update(2);
    assert.deepEqual(camera.position.toArray(), stopped.position.toArray(),
      "dừng camera khi rời cảnh/vào Explore phải dừng cả chuyến bay đang chạy");
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

// ── Bay tới badge khi hover, bay về khi rời ──────────────────────────────────

function createDollyHarness() {
  const document = new EventTarget();
  const element = Object.assign(new EventTarget(), {
    style: {}, ownerDocument: document, getRootNode: () => document,
  }) as unknown as HTMLElement;
  const camera = new THREE.PerspectiveCamera();
  const controls = new OrbitControls(camera, element);
  controls.maxPolarAngle = Math.PI / 2;
  const controller = createCameraController(camera, controls);
  return { camera, controls, controller };
}

/** Chạy animation loop giống tour-engine, để phát hiện giật do pose bị ghi đè. */
function runFrames(
  harness: ReturnType<typeof createDollyHarness>,
  seconds: number,
  frames = 60,
) {
  const delta = seconds / frames;
  for (let frame = 0; frame < frames; frame += 1) {
    // Giống tour-engine: cả hai đường cùng chạy, KHÔNG short-circuit. Nếu viết
    // `update() || updateDolly()` thì lúc có chuyến bay chuyển cảnh, `updateDolly()`
    // không bao giờ chạy và test không phát hiện được hai nguồn cùng ghi pose.
    const flying = harness.controller.update(delta);
    const dollyMoved = harness.controller.updateDolly(delta);
    if (!flying && !dollyMoved) harness.controls.update();
    harness.controller.syncPose();
  }
}

test("hover badge: camera bay tới trước badge rồi bay về đúng pose cũ khi rời", () => {
  const harness = createDollyHarness();
  const { camera, controls, controller } = harness;
  const badge = new THREE.Vector3(0, 0, 0);
  try {
    controller.applyPreset({ start_position: [0, 0, 10], start_target: [0, 0, -10] } as Parameters<typeof controller.applyPreset>[0]);
    const origin = camera.position.clone();
    const targetBefore = controls.target.clone();

    assert.equal(controller.setDollyTarget({ point: badge, approach: 0.3 }), true);
    // Nửa hành trình: đã lại gần nhưng chưa tới đích.
    runFrames(harness, 0.3);
    const middle = camera.position.distanceTo(badge);
    assert.ok(middle < origin.length() && middle > 3, `giữa hành trình ở ${middle}`);

    runFrames(harness, 0.7);
    // Đích: gần đúng tỉ lệ yêu cầu (10 × 0.3) và đang "đối mặt" badge.
    assert.ok(Math.abs(camera.position.distanceTo(badge) - 3) < 1e-6,
      `dừng ở ${camera.position.distanceTo(badge)}, mong đợi 3`);
    assert.ok(camera.position.y > 0, "góc máy phải ở phía trên badge để không bị địa hình che");
    const forward = camera.getWorldDirection(new THREE.Vector3());
    const toBadge = badge.clone().sub(camera.position).normalize();
    assert.ok(forward.dot(toBadge) > 0.999, "camera không hướng về badge");
    // Phải là mặt phẳng đứng (không nghiêng đầu): hướng lên gần như vuông góc trục ngang.
    assert.ok(Math.abs(camera.up.y) > 0.9, `up bị nghiêng: ${camera.up.toArray()}`);

    // Rời badge: bay VỀ đúng pose ban đầu.
    controller.setDollyTarget(null);
    runFrames(harness, 0.9);
    assert.ok(camera.position.distanceTo(origin) < 1e-8,
      `không về đúng pose cũ: ${camera.position.toArray()}`);
    assert.ok(controls.target.distanceTo(targetBefore) < 1e-8, "target không trở lại pose cũ");
  } finally {
    controls.dispose();
  }
});

test("hover rồi buông chuột: pose sau hover là góc mới, reset không kéo về preset xa", () => {
  const harness = createDollyHarness();
  const { camera, controls, controller } = harness;
  const badge = new THREE.Vector3(0, 0, 0);
  try {
    controller.applyPreset({ start_position: [0, 0, 10], start_target: [0, 0, -10] } as Parameters<typeof controller.applyPreset>[0]);
    controller.setDollyTarget({ point: badge, approach: 0.3 });
    runFrames(harness, 1);
    const near = camera.position.clone();
    assert.ok(Math.abs(near.distanceTo(badge) - 3) < 1e-6, `pose gần sai: ${near.toArray()}`);

    // Đổi cảnh: chốt pose đang thấy để cảnh mới bay tiếp từ đó.
    controller.releaseDolly();
    assert.ok(camera.position.distanceTo(near) < 1e-8, "releaseDolly làm camera nhảy");
    controller.reset(0);
    assert.ok(camera.position.distanceTo(near) < 1e-8, "reset kéo camera về preset xa badge");
  } finally {
    controls.dispose();
  }
});

test("kéo chuột giữa chừng: chuyến bay hover nhường quyền và không bay về nữa", () => {
  const harness = createDollyHarness();
  const { camera, controls, controller } = harness;
  const badge = new THREE.Vector3(0, 0, 0);
  try {
    controller.applyPreset({ start_position: [0, 0, 10], start_target: [0, 0, -10] } as Parameters<typeof controller.applyPreset>[0]);
    controller.setDollyTarget({ point: badge, approach: 0.3 });
    runFrames(harness, 0.2);
    // Người dùng kéo chuột: pose do controls ghi ⇒ chuyến bay hover phải nhường.
    controller.setPointerActive(true);
    camera.position.set(4, 3, 8);
    controller.syncPose();
    assert.equal(controller.hasDolly(), false, "kéo chuột không hủy chuyến bay hover");
    controller.setPointerActive(false);
    // Rời badge sau đó cũng không được bay về pose cũ (pose hiện tại là góc mới).
    const manual = camera.position.clone();
    controller.setDollyTarget(null);
    runFrames(harness, 1);
    assert.ok(camera.position.distanceTo(manual) < 1e-8, "camera bị kéo về sau khi người dùng quay tay");
  } finally {
    controls.dispose();
  }
});

test("rời hover trên nền timeline đã chạy xong: về đúng pose lúc bắt đầu hover", () => {
  const harness = createDollyHarness();
  const { camera, controls, controller } = harness;
  const badge = new THREE.Vector3(0, 0, 0);
  const preset = {
    start_position: [0, 0, 20],
    start_target: [0, 0, -20],
    zoom_position: [0, 4, 12],
    zoom_target: [0, 0, 0],
  } as Parameters<typeof controller.startTimeline>[0];
  try {
    // Timeline chạy hết ⇒ camera nghỉ ở zoom_position/zoom_target.
    assert.equal(controller.startTimeline(preset, 10), true);
    for (let frame = 0; frame < 200; frame += 1) {
      controller.updateTimeline(10);
    }
    runFrames(harness, 0.5);
    const entry = camera.position.clone();
    const entryTarget = controls.target.clone();
    assert.ok(entry.distanceTo(new THREE.Vector3(0, 4, 12)) < 1e-6,
      `chưa nghỉ ở điểm cuối timeline: ${entry.toArray()}`);

    // Hover badge rồi rời: "camera cũ" chính là pose lúc bắt đầu hover.
    assert.equal(controller.setDollyTarget({ point: badge, approach: 0.3 }), true);
    runFrames(harness, 1);
    assert.ok(camera.position.distanceTo(entry) > 1, "hover không đưa camera tới gần badge");

    controller.setDollyTarget(null);
    runFrames(harness, 1);
    assert.ok(camera.position.distanceTo(entry) < 1e-6,
      `rời hover không về pose lúc bắt đầu hover: ${camera.position.toArray()} vs ${entry.toArray()}`);
    assert.ok(controls.target.distanceTo(entryTarget) < 1e-6, "target không về pose lúc bắt đầu hover");
  } finally {
    controls.dispose();
  }
});

test("rời hover giữa timeline: về pose lúc bắt đầu hover (như exit mode), không nhảy về preset", () => {
  const harness = createDollyHarness();
  const { camera, controls, controller } = harness;
  const badge = new THREE.Vector3(0, 0, 0);
  const preset = {
    start_position: [0, 0, 20],
    start_target: [0, 0, -20],
    zoom_position: [6, 5, 10],
    zoom_target: [1, 1, 0],
  } as Parameters<typeof controller.startTimeline>[0];
  try {
    // Camera đang ở giữa timeline (chưa tới điểm cuối) — đây là "camera cũ".
    controller.startTimeline(preset, 10);
    controller.updateTimeline(0.5);
    controller.stopTimeline();
    const entry = camera.position.clone();
    const entryTarget = controls.target.clone();

    controller.setDollyTarget({ point: badge, approach: 0.3 });
    runFrames(harness, 1);
    assert.ok(camera.position.distanceTo(entry) > 1, "hover không đưa camera tới gần badge");

    controller.setDollyTarget(null);
    runFrames(harness, 1);
    assert.ok(camera.position.distanceTo(entry) < 1e-6,
      `không về đúng pose lúc bắt đầu hover: ${camera.position.toArray()} vs ${entry.toArray()}`);
    assert.ok(controls.target.distanceTo(entryTarget) < 1e-6, "target không về pose lúc bắt đầu hover");
    // Không được nhảy về điểm cuối timeline (hành vi cũ, đã bỏ).
    assert.ok(camera.position.distanceTo(new THREE.Vector3(6, 5, 10)) > 1,
      "lại nhảy về điểm cuối timeline thay vì pose lúc bắt đầu hover");
  } finally {
    controls.dispose();
  }
});

test("hover bắt đầu GIỮA chuyến bay chuyển cảnh: camera cũ là ĐÍCH của chuyến bay", () => {
  const harness = createDollyHarness();
  const { camera, controls, controller } = harness;
  const badge = new THREE.Vector3(0, 0, 0);
  const deepLive = new THREE.Vector3(4, 3, 12);
  try {
    controller.applyPreset({
      start_position: [0, 0, 40],
      start_target: [0, 0, -40],
    } as Parameters<typeof controller.applyPreset>[0]);
    // Bật deep live: camera bay 1.6s từ góc cũ tới góc mặc định của chế độ này.
    assert.equal(
      controller.flyToPreset(
        {
          start_position: [deepLive.x, deepLive.y, deepLive.z],
          start_target: [0, 0, 0],
        } as Parameters<typeof controller.flyToPreset>[0],
        false,
        1.6,
      ),
      true,
    );
    // Mới đi được một đoạn: pose hiện tại KHÔNG phải góc mặc định của deep live.
    runFrames(harness, 0.4);
    const midFlight = camera.position.clone();
    assert.ok(midFlight.distanceTo(deepLive) > 1, `chưa tới đích chuyến bay: ${midFlight.toArray()}`);
    assert.equal(controller.isFlying(), true, "chuyến bay chuyển cảnh phải còn đang chạy");

    // Người dùng hover badge ngay giữa chuyến bay.
    assert.equal(controller.setDollyTarget({ point: badge, approach: 0.3 }), true);
    // Chuyến bay phải nhường quyền, không cùng ghi pose với dolly mỗi frame.
    // (Nếu không nhường thì "camera cũ" cũng bị chụp sai thành điểm giữa đường.)
    assert.equal(controller.isFlying(), false,
      "chuyến bay chuyển cảnh không nhường hover ⇒ hai nguồn cùng ghi pose mỗi frame");

    runFrames(harness, 1);
    assert.ok(camera.position.distanceTo(badge) < midFlight.distanceTo(badge),
      "hover không đưa camera lại gần badge");

    // Rời badge ⇒ về ĐÍCH của chuyến bay (góc mặc định deep live), KHÔNG phải điểm giữa đường.
    controller.setDollyTarget(null);
    runFrames(harness, 1);
    assert.ok(camera.position.distanceTo(deepLive) < 1e-6,
      `không về góc mặc định của deep live: ${camera.position.toArray()} vs ${deepLive.toArray()}`);
    assert.ok(camera.position.distanceTo(midFlight) > 1,
      "lại quay về điểm giữa đường của chuyến bay chuyển cảnh");
    assert.ok(controls.target.distanceTo(new THREE.Vector3(0, 0, 0)) < 1e-6,
      `target không về góc mặc định: ${controls.target.toArray()}`);
  } finally {
    controls.dispose();
  }
});

test("hover liên tiếp nhiều badge: không cộng dồn zoom, rời ra về đúng góc gốc", () => {
  const harness = createDollyHarness();
  const { camera, controls, controller } = harness;
  const badge2 = new THREE.Vector3(0, 0, 0);
  const badge3 = new THREE.Vector3(8, 0, 6);
  const approach = 0.3;
  try {
    controller.applyPreset({
      start_position: [0, 0, 40],
      start_target: [0, 0, -40],
    } as Parameters<typeof controller.applyPreset>[0]);
    const origin = camera.position.clone();
    const target0 = controls.target.clone();
    // Cự ly dừng kỳ vọng neo vào GÓC GỐC, không phải vị trí camera lúc bấy giờ.
    const expect = (badge: THREE.Vector3) => origin.distanceTo(badge) * approach;

    // Lần 1: badge 2.
    controller.setDollyTarget({ point: badge2, approach });
    runFrames(harness, 1);
    const first = camera.position.distanceTo(badge2);
    assert.ok(Math.abs(first - expect(badge2)) < 1e-6,
      `lần 1 dừng ở ${first}, mong đợi ${expect(badge2)}`);

    // Chuyển thẳng sang badge 3 (hai badge sát nhau, con trỏ không đi qua khoảng trống).
    controller.setDollyTarget({ point: badge3, approach });
    runFrames(harness, 1);
    const second = camera.position.distanceTo(badge3);
    assert.ok(Math.abs(second - expect(badge3)) < 1e-6,
      `lần 2 cộng dồn zoom: dừng ở ${second}, mong đợi ${expect(badge3)}`);
    assert.ok(second > first * 0.5, `zoom bị cộng dồn: ${first} → ${second}`);

    // Rời badge 3 rồi vào lại badge 2 NGAY (chuyến bay về còn đang chạy giữa chừng).
    controller.setDollyTarget(null);
    runFrames(harness, 0.3);
    controller.setDollyTarget({ point: badge2, approach });
    runFrames(harness, 1);
    const back = camera.position.distanceTo(badge2);
    assert.ok(Math.abs(back - first) < 1e-6,
      `quay lại badge 2 bị cộng dồn zoom: ${first} → ${back}`);

    // Rời hẳn ⇒ về đúng góc gốc ban đầu, không trôi dần theo từng lần hover.
    controller.setDollyTarget(null);
    runFrames(harness, 1);
    assert.ok(camera.position.distanceTo(origin) < 1e-6,
      `không về góc gốc: ${camera.position.toArray()} vs ${origin.toArray()}`);
    assert.ok(controls.target.distanceTo(target0) < 1e-6, "target trôi khỏi góc gốc");
  } finally {
    controls.dispose();
  }
});

test("sàn khoảng cách hover không để badge lọt vào trong mặt phẳng cắt gần", () => {
  const harness = createDollyHarness();
  const { camera, controls, controller } = harness;
  const badge = new THREE.Vector3(0, 0, 0);
  try {
    // near lớn là tình huống thật: model có địa hình xa làm bán kính bounding sphere phình to.
    camera.near = 5;
    controller.applyPreset({
      start_position: [0, 0, 40],
      start_target: [0, 0, -40],
    } as Parameters<typeof controller.applyPreset>[0]);
    // approach rất nhỏ ⇒ khoảng cách đích 2, tức nằm sâu trong `near`.
    controller.setDollyTarget({ point: badge, approach: 0.05, minDistance: 0.6 });
    runFrames(harness, 1);
    const distance = camera.position.distanceTo(badge);
    assert.ok(distance > camera.near,
      `badge lọt vào trong near (${distance} ≤ ${camera.near}) ⇒ bị xén mất khỏi màn hình`);
    assert.ok(distance >= camera.near * 2 - 1e-6, `không áp sàn near: ${distance}`);
  } finally {
    controls.dispose();
  }
});

// ── Chống dao động hover (camera tự bay làm badge trượt khỏi con trỏ) ─────────

test("shouldEvaluateHover: bỏ raycast khi đang bay tới badge và khi chuột chỉ rung", () => {
  const still = { x: 0, y: 0 };
  // Chưa có mốc con trỏ ⇒ phải đánh giá.
  assert.equal(shouldEvaluateHover(still, { x: NaN, y: NaN }, false), true);
  // Con trỏ đứng yên ⇒ không đổi trạng thái hover.
  assert.equal(shouldEvaluateHover(still, still, false), false);
  // Rung vài pixel (dưới ngưỡng) ⇒ vẫn coi như đứng yên.
  assert.equal(shouldEvaluateHover({ x: 0.005, y: -0.008 }, still, false), false);
  // Di chuyển thật ⇒ đánh giá lại.
  assert.equal(shouldEvaluateHover({ x: 0.3, y: 0 }, still, false), true);
  // Đang bay tới badge ⇒ luôn bỏ qua, dù con trỏ có di chuyển xa.
  assert.equal(shouldEvaluateHover({ x: 0.9, y: 0.9 }, still, true), false);
});

test("isApproaching: chỉ true khi đang trên đường bay TỚI badge, không phải lúc bay về", () => {
  const harness = createDollyHarness();
  const { camera, controls, controller } = harness;
  const badge = new THREE.Vector3(0, 0, 0);
  try {
    controller.applyPreset({ start_position: [0, 0, 10], start_target: [0, 0, -10] } as Parameters<typeof controller.applyPreset>[0]);
    assert.equal(controller.isApproaching(), false, "chưa hover mà đã báo đang bay tới");
    controller.setDollyTarget({ point: badge, approach: 0.3 });
    assert.equal(controller.isApproaching(), true, "đang bay tới badge mà không báo");
    runFrames(harness, 1);
    assert.equal(controller.isApproaching(), false, "đã chốt pose ở badge mà vẫn báo đang bay");
    // Rời badge ⇒ đang bay VỀ, phải cho phép raycast lại để người dùng hover tiếp.
    controller.setDollyTarget(null);
    assert.equal(controller.isApproaching(), false, "chuyến bay về bị coi là bay tới");
  } finally {
    controls.dispose();
  }
});

test("dao động hover: con trỏ đứng yên + camera bay vào ⇒ hover không lật liên tục", () => {
  const harness = createDollyHarness();
  const { camera, controls, controller } = harness;
  const badge = new THREE.Vector3(0, 0, 0);
  try {
    controller.applyPreset({ start_position: [0, 0, 20], start_target: [0, 0, -20] } as Parameters<typeof controller.applyPreset>[0]);
    const startDist = camera.position.distanceTo(badge);

    // Mô phỏng onPointerMove: con trỏ đứng yên nên sau lần đầu không đánh giá lại,
    // và trong lúc camera bay tới badge thì bỏ qua hẳn.
    const last = new THREE.Vector2(NaN, NaN);
    const pointer = new THREE.Vector2(0.1, 0.1);
    let flips = 0;
    let hovered = false;
    for (let frame = 0; frame < 180; frame += 1) {
      if (shouldEvaluateHover(pointer, last, controller.isApproaching())) {
        last.copy(pointer);
        // Raycast "trượt" sau khi camera đã bay vào (badge trượt khỏi con trỏ).
        const nowOnBadge = frame < 5;
        if (nowOnBadge !== hovered) {
          hovered = nowOnBadge;
          flips += 1;
          controller.setDollyTarget(nowOnBadge ? { point: badge, approach: 0.3 } : null);
        }
      }
      const driven = controller.update(1 / 60) || controller.updateDolly(1 / 60);
      if (!driven) controls.update();
      controller.syncPose();
    }

    assert.equal(flips, 1, `hover lật ${flips} lần (phải 1 lần duy nhất)`);
    // Camera phải bay vào tới đích, không bị kẹt giữa đường vì hover bị hủy.
    assert.ok(Math.abs(camera.position.distanceTo(badge) - startDist * 0.3) < 1e-6,
      `camera kẹt ở ${camera.position.distanceTo(badge)}, mong đợi ${startDist * 0.3}`);
  } finally {
    controls.dispose();
  }
});

// ── Sàn minDistance không được kéo camera vọt ra xa ──────────────────────────

test("model lớn: sàn minDistance suy từ pose tác giả, không kéo camera vọt ra xa", () => {
  const harness = createDollyHarness();
  const { camera, controls, controller } = harness;
  const badge = new THREE.Vector3(0, 0, 0);
  try {
    // Model rất lớn (địa hình xa) ⇒ bán kính model lớn hơn nhiều so với pose tác giả.
    // Đây đúng là điều kiện model Petra: sàn từ bán kính model sẽ là ~hàng nghìn.
    controller.fit(new THREE.Mesh(new THREE.BoxGeometry(50000, 50000, 50000)));
    const modelFloor = controls.minDistance;
    assert.ok(modelFloor > 1000, `sàn từ model phải rất lớn để tái hiện lỗi: ${modelFloor}`);

    controller.applyPreset({
      start_position: [20, 10, 0],
      start_target: [0, 0, 0],
    } as Parameters<typeof controller.applyPreset>[0]);
    const entry = camera.position.clone();
    const entryDistance = entry.distanceTo(badge);
    // Sàn phải được suy lại từ pose tác giả (nửa khoảng cách pose).
    assert.ok(controls.minDistance < entryDistance,
      `sàn chưa suy từ pose tác giả: ${controls.minDistance} vs pose ${entryDistance}`);

    controller.setDollyTarget({ point: badge, approach: 0.3, minDistance: 0.6 });
    runFrames(harness, 1);
    const near = camera.position.clone();
    assert.ok(Math.abs(near.distanceTo(badge) - entryDistance * 0.3) < 1e-6,
      `không tới đúng đích: ${near.distanceTo(badge)} thay vì ${entryDistance * 0.3}`);

    // Lỗi cũ: frame rảnh sau khi chuyến hover kết thúc bị OrbitControls kéo vọt ra xa.
    runFrames(harness, 1);
    assert.ok(camera.position.distanceTo(near) < 1e-6,
      `camera bị kéo vọt ra xa sau hover: ${camera.position.toArray()}`);

    // Và rời badge cũng phải về đúng "camera cũ", không qua chỗ xa.
    controller.setDollyTarget(null);
    runFrames(harness, 1);
    assert.ok(camera.position.distanceTo(entry) < 1e-6,
      `không về đúng camera cũ: ${camera.position.toArray()} vs ${entry.toArray()}`);
  } finally {
    controls.dispose();
  }
});

// ── Chế độ đi bộ (`free_explore`): OBB, độ cao mắt, cần gạt ảo ───────────────

/** Hộp thẳng trục cho dễ đọc toạ độ trong assertion. */
const FLAT_AREA: ExploreArea = {
  center: [0, 0, 0],
  extents: [10, 5, 10],
  rotation: [0, 0, 0, 1],
};

/** Hộp xoay 90° quanh Y: trục X cục bộ trỏ về −Z thế giới. */
const YAWED_AREA: ExploreArea = {
  center: [0, 0, 0],
  extents: [2, 1, 5],
  rotation: [0, Math.SQRT1_2, 0, Math.SQRT1_2],
};

/**
 * `createWalkInput` và `OrbitControls` chạm vào `window` / `HTMLElement` — Node
 * không có hai thứ đó. Cài bản tối thiểu quanh mỗi test rồi gỡ ra.
 */
function installDomGlobals() {
  const globals = globalThis as unknown as Record<string, unknown>;
  const previous = {
    window: globals.window,
    document: globals.document,
    HTMLElement: globals.HTMLElement,
  };

  class StubHTMLElement extends EventTarget {
    style: Record<string, string> = {};
    ownerDocument: EventTarget = new EventTarget();
    getRootNode() { return this.ownerDocument; }
  }

  globals.HTMLElement = StubHTMLElement;
  globals.window = new EventTarget();
  globals.document = new EventTarget();

  return {
    window: globals.window as EventTarget,
    createElement: () => new StubHTMLElement() as unknown as HTMLElement,
    restore() {
      globals.window = previous.window;
      globals.document = previous.document;
      globals.HTMLElement = previous.HTMLElement;
    },
  };
}

/** Phát một sự kiện có thuộc tính tuỳ biến (`key`, `pointerId`, `clientX`…). */
function emit(target: EventTarget, type: string, init: Record<string, unknown>) {
  const event = new Event(type);
  Object.assign(event, init);
  target.dispatchEvent(event);
}

function createWalkHarness(area: ExploreArea | null) {
  const dom = installDomGlobals();
  const canvas = dom.createElement();
  const camera = new THREE.PerspectiveCamera();
  const controls = new OrbitControls(camera, canvas);
  controls.maxPolarAngle = Math.PI / 2;
  // Giống `fit()` trên model Petra: sàn lớn hơn hẳn điểm neo 1 đơn vị — đây
  // chính là lý do chế độ đi bộ phải tự ghi pose thay vì gọi `controls.update()`.
  controls.minDistance = 1.23;
  controls.maxDistance = 400;
  const controller = createCameraController(camera, controls);

  /** Mọi lần tường biên được cập nhật, để kiểm tra nó chạy cả khi đứng yên. */
  const boundaryCalls: (ExploreArea | null)[] = [];
  const boundary = {
    update: (_camera: THREE.Camera, next: ExploreArea | null) => {
      boundaryCalls.push(next);
      return false;
    },
    show: (_visible: boolean) => {},
    dispose: () => {},
  };

  const explore = createExploreController(controller, controls, { camera, canvas, boundary });
  // Biên đi bộ là state của CẢNH, không phải tham số lúc dựng: engine nhận nó
  // qua `setExploreArea` khi cảnh đổi.
  explore.setArea(area);
  return { ...dom, canvas, camera, controls, controller, explore, boundaryCalls };
}

test("parseExploreArea nhận chuỗi JSON lẫn object, chối dữ liệu hỏng", () => {
  const area: ExploreArea = { center: [1, 2, 3], extents: [4, 5, 6], rotation: [0, 0, 0, 1] };
  // Bản gốc lưu CHUỖI JSON; cột JSONB của backend trả OBJECT đã tách sẵn.
  assert.deepEqual(parseExploreArea(JSON.stringify(area)), area);
  assert.deepEqual(parseExploreArea(area), area);

  assert.equal(parseExploreArea(null), null);
  assert.equal(parseExploreArea(undefined), null);
  assert.equal(parseExploreArea(""), null);
  assert.equal(parseExploreArea("{không phải json"), null);
  assert.equal(parseExploreArea(42), null);
  assert.equal(parseExploreArea({ ...area, center: [1, 2] }), null);
  assert.equal(parseExploreArea({ ...area, rotation: [0, 0, 0] }), null);
  // Cạnh suy biến làm hộp mất chiều ⇒ coi như dữ liệu hỏng.
  assert.equal(parseExploreArea({ ...area, extents: [4, 0, 6] }), null);
  assert.equal(parseExploreArea({ ...area, extents: [4, -5, 6] }), null);
  assert.equal(parseExploreArea({ ...area, center: [1, 2, Number.NaN] }), null);
});

test("kẹp OBB: trong hộp giữ nguyên, ngoài hộp kéo về mặt gần nhất, tôn trọng xoay", () => {
  // Trong hộp (kể cả đúng trên mặt) ⇒ không đụng tới.
  const inside = new THREE.Vector3(9.5, 4.5, -9.5);
  assert.equal(clampPointToExploreArea(inside, FLAT_AREA), false);
  assert.deepEqual(inside.toArray(), [9.5, 4.5, -9.5]);

  const onFace = new THREE.Vector3(10, 5, 10);
  assert.equal(clampPointToExploreArea(onFace, FLAT_AREA), false);
  assert.deepEqual(onFace.toArray(), [10, 5, 10]);

  // `extents` là NỬA cạnh: (50, 40, −50) phải về đúng (±10, ±5, ∓10).
  const outside = new THREE.Vector3(50, 40, -50);
  assert.equal(clampPointToExploreArea(outside, FLAT_AREA), true);
  assert.deepEqual(outside.toArray(), [10, 5, -10]);

  // Hộp xoay 90° quanh Y: X cục bộ → −Z thế giới, Z cục bộ → +X thế giới.
  // Nửa cạnh (2, 1, 5) ⇒ hộp thế giới là x ∈ [−5, 5], y ∈ [−1, 1], z ∈ [−2, 2].
  const sideways = new THREE.Vector3(0, 0, -4);
  assert.equal(clampPointToExploreArea(sideways, YAWED_AREA), true);
  assert.ok(sideways.distanceTo(new THREE.Vector3(0, 0, -2)) < 1e-12,
    `kẹp theo trục cục bộ sai: ${sideways.toArray()}`);

  const along = new THREE.Vector3(9, 0, 0);
  assert.equal(clampPointToExploreArea(along, YAWED_AREA), true);
  assert.ok(along.distanceTo(new THREE.Vector3(5, 0, 0)) < 1e-12,
    `kẹp theo trục cục bộ sai: ${along.toArray()}`);

  // Điểm trong hộp xoay vẫn phải giữ nguyên.
  const insideYawed = new THREE.Vector3(4, 0.5, 1.5);
  assert.equal(clampPointToExploreArea(insideYawed, YAWED_AREA), false);
});

test("cần gạt ảo: chỉ tính khi kéo quá vùng chết, kéo xuống là lùi, kéo ngang là quay", () => {
  const dom = installDomGlobals();
  const canvas = dom.createElement();
  const input = createWalkInput(canvas);
  try {
    input.attach();
    assert.deepEqual(input.read(), { forward: 0, strafe: 0, turn: 0 });

    emit(canvas, "pointerdown", { pointerId: 1, clientX: 0, clientY: 0 });
    // Trong vùng chết ⇒ coi như đứng yên (nếu không, rung tay vài pixel đã quay).
    emit(canvas, "pointermove", {
      pointerId: 1,
      clientX: INPUT_DEAD_ZONE * DRAG_RADIUS - 1,
      clientY: 0,
    });
    assert.deepEqual(input.read(), { forward: 0, strafe: 0, turn: 0 });

    // Kéo đủ xa sang phải + xuống dưới: quay phải, đi lùi.
    emit(canvas, "pointermove", { pointerId: 1, clientX: DRAG_RADIUS, clientY: DRAG_RADIUS });
    assert.deepEqual(input.read(), { forward: -1, strafe: 0, turn: 1 });

    // Nhả tay ⇒ về 0 ngay, không giữ lại đà.
    emit(canvas, "pointerup", { pointerId: 1, clientX: DRAG_RADIUS, clientY: DRAG_RADIUS });
    assert.deepEqual(input.read(), { forward: 0, strafe: 0, turn: 0 });

    // WASD cộng dồn với cần gạt.
    emit(dom.window, "keydown", { key: "w" });
    emit(dom.window, "keydown", { key: "d" });
    assert.deepEqual(input.read(), { forward: 1, strafe: 1, turn: 0 });
    // Mất focus giữa chừng không được để kẹt phím.
    emit(dom.window, "blur", {});
    assert.deepEqual(input.read(), { forward: 0, strafe: 0, turn: 0 });
  } finally {
    input.detach();
    dom.restore();
  }
});

test("chế độ đi bộ: khoá độ cao mắt, kẹp biên, tắt orbit và trả lại khi thoát", () => {
  const harness = createWalkHarness(FLAT_AREA);
  const { camera, controls, explore, boundaryCalls } = harness;
  try {
    camera.position.set(10, 40, -3);
    camera.lookAt(10, 40, -13);
    camera.updateMatrixWorld(true);

    assert.equal(explore.isWalking(), false);
    explore.enter("walk", 4.775);

    assert.equal(explore.isWalking(), true);
    // OrbitControls phải nhường hẳn: nó kẹp khoảng cách về [minDistance, maxDistance]
    // và điểm neo chỉ cách 1 đơn vị, nên nếu còn chạy sẽ đẩy camera mỗi frame.
    assert.equal(controls.enableRotate, false);
    assert.equal(controls.enablePan, false);
    assert.equal(controls.enableZoom, false);
    assert.equal(controls.maxPolarAngle, Math.PI);

    // Frame đầu: mắt tụt xuống đúng độ cao của điểm tương tác.
    assert.equal(explore.updateWalk(1 / 60), true);
    assert.equal(camera.position.y, 4.775);
    assert.deepEqual(camera.position.toArray(), [10, 4.775, -3]);

    // Ra ngoài hộp ⇒ kéo về mặt gần nhất rồi mới ép độ cao.
    camera.position.set(50, 40, -50);
    explore.updateWalk(1 / 60);
    assert.deepEqual(camera.position.toArray(), [10, 4.775, -10]);

    // Đứng yên thì không ghi pose, nhưng tường biên vẫn phải được cập nhật.
    const callsBefore = boundaryCalls.length;
    assert.equal(explore.updateWalk(1 / 60), false);
    assert.equal(boundaryCalls.length, callsBefore + 1);
    assert.equal(boundaryCalls.at(-1), FLAT_AREA);

    // Giữ W: đi đúng theo hướng nhìn, luôn nằm ngang, và điểm neo cách 1 đơn vị.
    camera.position.set(0, 4.775, 0);
    camera.lookAt(0, 4.775, -10);
    camera.updateMatrixWorld(true);
    emit(harness.window, "keydown", { key: "w" });
    explore.updateWalk(0.1);
    assert.ok(Math.abs(camera.position.z + WALK_SPEED * 0.1) < 1e-9,
      `đi sai quãng đường: ${camera.position.toArray()}`);
    assert.equal(camera.position.x, 0);
    assert.equal(camera.position.y, 4.775);
    assert.ok(Math.abs(controls.target.z - (camera.position.z - 1)) < 1e-9);
    assert.equal(controls.target.y, 4.775);

    // Thoát ⇒ nhả phím, trả lại orbit và ẩn tường.
    explore.exit();
    assert.equal(explore.isWalking(), false);
    assert.equal(controls.enableRotate, true);
    assert.equal(controls.enablePan, true);
    assert.equal(controls.enableZoom, true);
    assert.equal(controls.maxPolarAngle, Math.PI / 2);
    assert.equal(explore.updateWalk(1 / 60), false);
  } finally {
    harness.restore();
  }
});

test("Reset trong chế độ đi bộ không nhấc mắt lên theo pose trước khi vào", () => {
  const harness = createWalkHarness(FLAT_AREA);
  const { camera, explore } = harness;
  try {
    camera.position.set(0, 80, 0);
    camera.lookAt(0, 80, -10);
    camera.updateMatrixWorld(true);

    explore.enter("walk", 4.775);
    explore.updateWalk(1 / 60);
    assert.equal(camera.position.y, 4.775);

    camera.position.set(3, 4.775, -2);
    explore.reset();

    // `reset` về pose lúc vào (y = 80) — nhưng mắt phải được kéo lại 4,775 ngay
    // frame sau, không thì người đi bộ bị nhấc lơ lửng trên không.
    explore.updateWalk(1 / 60);
    assert.equal(camera.position.y, 4.775);
  } finally {
    harness.restore();
  }
});

test("đi bộ nhường quyền cho chuyến bay vào chế độ, chỉ khoá mắt sau khi tới", () => {
  const harness = createWalkHarness(FLAT_AREA);
  const { camera, controller, explore } = harness;
  try {
    camera.position.set(0, 60, 0);
    camera.lookAt(0, 60, -10);
    camera.updateMatrixWorld(true);

    explore.enter("walk", 4.775);
    // Bay 1,2s tới điểm xuất phát — giống `applyInteractiveCamera` của player.
    controller.flyToPreset(
      { start_position: [3, 4.775, -2], start_target: [3, 4.775, -3] } as Parameters<typeof controller.flyToPreset>[0],
      false,
      1.2,
    );

    // Đang bay: đi bộ KHÔNG ghi pose, nên camera còn ở trên cao chứ không nhảy
    // phóc về 4,775 giữa chừng.
    assert.equal(explore.updateWalk(0.3), false);
    assert.ok(camera.position.y > 4.775, `mắt bị khoá sớm: y=${camera.position.y}`);

    controller.update(1.2);
    assert.equal(controller.isFlying(), false);
    assert.ok(Math.abs(camera.position.y - 4.775) < 1e-9);
    assert.ok(camera.position.distanceTo(new THREE.Vector3(3, 4.775, -2)) < 1e-9);

    // Tới nơi rồi thì đi bộ nhận quyền trở lại.
    emit(harness.window, "keydown", { key: "w" });
    assert.equal(explore.updateWalk(0.1), true);
    assert.equal(camera.position.y, 4.775);
  } finally {
    harness.restore();
  }
});

test("đổi vùng đi bộ giữa chừng thì frame sau đã kẹp theo biên mới", () => {
  const harness = createWalkHarness(null);
  const { camera, explore, boundaryCalls } = harness;
  try {
    camera.position.set(0, 4.775, 0);
    camera.lookAt(0, 4.775, -10);
    camera.updateMatrixWorld(true);

    explore.enter("walk", 4.775);
    explore.updateWalk(1 / 60);
    // Chưa biết biên ⇒ chỉ khoá độ cao, không kẹp gì.
    assert.equal(boundaryCalls.at(-1), null);
    assert.equal(camera.position.y, 4.775);

    explore.setArea(YAWED_AREA);
    camera.position.set(0, 4.775, -40);
    explore.updateWalk(1 / 60);
    assert.equal(boundaryCalls.at(-1), YAWED_AREA);
    assert.ok(camera.position.distanceTo(new THREE.Vector3(0, 4.775, -2)) < 1e-12,
      `chưa kẹp theo biên mới: ${camera.position.toArray()}`);
  } finally {
    harness.restore();
  }
});
