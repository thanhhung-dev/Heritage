import assert from "node:assert/strict";
import test from "node:test";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { createCameraController } from "../features/tour/three/camera-controller";
import { TEST_TOUR } from "../features/tour/tour-data";
import { createSceneDraft, parseSceneDraft, sampleSceneDraft } from "../features/tour/dev/scene-draft";

test("editor permits close zoom after pose edits and restores normal tour constraints", () => {
  const document = new EventTarget();
  const element = Object.assign(new EventTarget(), {
    style: {}, ownerDocument: document, getRootNode: () => document,
  }) as unknown as HTMLElement;
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
  camera.position.set(0, 0, 100);
  const controls = new OrbitControls(camera, element);
  controls.minDistance = 80;
  controls.enableZoom = false;
  controls.enablePan = false;
  const controller = createCameraController(camera, controls);
  try {
    const finishEditing = controller.enableEditing();
    assert.equal(controls.enableZoom, true);
    assert.equal(controls.enablePan, true);
    controller.restore({ ...controller.snapshot(), position: new THREE.Vector3(0, 0, 30) });
    camera.position.set(0, 0, 10);
    controls.update();
    assert.ok(Math.abs(camera.position.distanceTo(controls.target) - 10) < 1e-8);
    controller.restore({ ...controller.snapshot(), position: new THREE.Vector3(0, 0, 100) });
    finishEditing();
    assert.equal(controls.enableZoom, false);
    assert.equal(controls.enablePan, false);
    assert.equal(controls.minDistance, 80);
  } finally { controls.dispose(); }
});

test("scene draft round trips without changing source scene and rejects another scene's draft", () => {
  const scene = structuredClone(TEST_TOUR.payload.scenes[0]);
  const original = structuredClone(scene);
  const draft = createSceneDraft("lang-tu-duc", "s1", scene);
  draft.title = "Góc nhà bia";
  draft.start = { position: [2, 8, -4], target: [1, 2, 3], up: [0, 1, 0], fov: 50 };
  draft.end = { position: [18, 4, 12], target: [-3, 6, 7], up: [0, 1, 0], fov: 50 };
  assert.deepEqual(parseSceneDraft(JSON.stringify(draft), "lang-tu-duc", "s1", scene.id), draft);
  assert.equal(parseSceneDraft(JSON.stringify(draft), "cung-an-dinh", "s1", scene.id), null);
  assert.equal(parseSceneDraft(JSON.stringify(draft), "lang-tu-duc", "s2", scene.id), null);
  assert.equal(parseSceneDraft(JSON.stringify(draft), "lang-tu-duc", "s1", scene.id + 1), null);
  assert.deepEqual(scene, original);
});

test("A → B preview seeks asymmetrically, clamps endpoints and never changes captured poses", () => {
  const draft = createSceneDraft("lang-tu-duc", "s1", TEST_TOUR.payload.scenes[0]);
  draft.durationSeconds = 8;
  draft.start = { position: [2, 8, -4], target: [1, 2, 3], up: [0, 1, 0], fov: 50 };
  draft.end = { position: [18, 4, 12], target: [-3, 6, 7], up: [0, 1, 0], fov: 70 };
  const before = structuredClone(draft);
  assert.deepEqual(sampleSceneDraft(draft, 2), {
    position: [6, 7, 0], target: [0, 3, 4], up: [0, 1, 0], fov: 55,
  });
  assert.deepEqual(sampleSceneDraft(draft, 20), draft.end);
  assert.deepEqual(sampleSceneDraft(draft, -1), draft.start);
  sampleSceneDraft(draft, 7);
  assert.deepEqual(sampleSceneDraft(draft, 2)?.position, [6, 7, 0]);
  assert.deepEqual(draft, before);
  draft.end = null;
  assert.equal(sampleSceneDraft(draft, 2), null);
});

test("draft loading rejects broken numeric data and preserves explicit GLB path opt-in", () => {
  const scene = { ...TEST_TOUR.payload.scenes[0], camera: { ...TEST_TOUR.payload.scenes[0].camera, path_url: "camera.glb" } };
  const draft = createSceneDraft("lang-tu-duc", "s1", scene);
  assert.equal(draft.useAB, false);
  for (const invalid of ["not json", JSON.stringify({ ...draft, version: 2 }), JSON.stringify({ ...draft, durationSeconds: 0 }), JSON.stringify({ ...draft, durationSeconds: null }), JSON.stringify({ ...draft, start: { position: [1, 2], target: [1, 2, 3], up: [0, 1, 0], fov: 50 } })]) {
    assert.equal(parseSceneDraft(invalid, "lang-tu-duc", "s1", scene.id), null);
  }
  draft.useAB = true;
  assert.equal(parseSceneDraft(JSON.stringify(draft), "lang-tu-duc", "s1", scene.id)?.useAB, true);
});
