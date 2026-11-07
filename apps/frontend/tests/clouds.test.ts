import assert from "node:assert/strict";
import test from "node:test";
import * as THREE from "three";
import { createClouds } from "../features/tour/three/clouds";

test("cloud animation only requests frames for presets with visible clouds", () => {
  const scene = new THREE.Scene();
  const clouds = createClouds(scene, new THREE.CubeTexture());
  try {
    clouds.apply(0, 0, new THREE.Vector3(0, 1, 0));
    assert.equal(clouds.update(0.1), false);
    clouds.apply(0.35, 0.55, new THREE.Vector3(0, 1, 0));
    assert.equal(clouds.update(0.1), true);
    clouds.apply(0, 0.55, new THREE.Vector3(0, 1, 0));
    assert.equal(clouds.update(0.1), false, "clear-sky preset must stop animation");
    clouds.apply(0.35, 0, new THREE.Vector3(0, 1, 0));
    assert.equal(clouds.update(0.1), false, "zero-density clouds must not keep rendering");
  } finally { clouds.dispose(); }
});

test("cloud motion is throttled instead of forcing every idle frame to render", () => {
  const clouds = createClouds(new THREE.Scene(), new THREE.CubeTexture());
  try {
    clouds.apply(0.4, 0.6, new THREE.Vector3(0, 1, 0));
    assert.equal(clouds.update(0), false);
    let renders = 0;
    for (let frame = 0; frame < 120; frame += 1) {
      if (clouds.update(1 / 120)) renders += 1;
    }
    assert.ok(renders >= 10 && renders <= 30, `requested ${renders} renders in one second`);
  } finally { clouds.dispose(); }
});

test("hidden tabs and reduced motion stop cloud animation; dispose leaves tour objects intact", () => {
  const previousWindow = globalThis.window;
  const previousDocument = globalThis.document;
  const preference = { matches: false };
  const document = { hidden: false };
  globalThis.window = { matchMedia: () => preference } as unknown as Window & typeof globalThis;
  globalThis.document = document as Document;
  const scene = new THREE.Scene();
  const model = new THREE.Group();
  scene.add(model);
  const clouds = createClouds(scene, new THREE.CubeTexture());
  try {
    clouds.apply(0.3, 0.5, new THREE.Vector3(0, -0.1, 1));
    assert.equal(clouds.update(0.1), true);
    preference.matches = true;
    assert.equal(clouds.update(0.1), false);
    preference.matches = false;
    document.hidden = true;
    assert.equal(clouds.update(0.1), false);
    document.hidden = false;
    assert.equal(clouds.update(0.1), true);
    clouds.dispose();
    assert.deepEqual(scene.children, [model]);
  } finally {
    globalThis.window = previousWindow;
    globalThis.document = previousDocument;
  }
});
