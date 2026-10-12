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
