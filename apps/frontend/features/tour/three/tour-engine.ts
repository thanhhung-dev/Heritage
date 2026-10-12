import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { HeritageCamera, HeritageInteractiveHighlight } from "@/types/heritage";
import { setupEnvironment } from "./environment";
import { createModelLoader } from "./model-loader";
import { createCameraController } from "./camera-controller";
import { createExploreController, type ExploreMode } from "./explore-controller";
import { createInteractiveHighlights } from "./interactive-highlights";
import { createSceneHighlights, type TimedSceneHighlight } from "./scene-highlights";

export function createTourEngine(
  host: HTMLDivElement,
  modelUrl: string,
  onStatus: (message: string | null) => void,
  onError: (error: unknown) => void,
) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  renderer.domElement.setAttribute("aria-label", "Model 3D — kéo để xoay, cuộn để zoom");
  host.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  setupEnvironment(scene, renderer);

  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.maxPolarAngle = Math.PI / 2;
  const cameraController = createCameraController(camera, controls);
  const explore = createExploreController(cameraController, controls);
  const loader = createModelLoader(renderer);
  const highlights = createInteractiveHighlights(scene);
  let needsRender = true;
  const invalidate = () => { needsRender = true; };
  const timedHighlights = createSceneHighlights(scene, loader, invalidate);
  let playbackTime = 0;
  let glbCameras: THREE.Camera[] = [];
  let disposed = false;
  const resize = () => {
    const { width, height } = host.getBoundingClientRect();
    if (!width || !height) return;
    explore.resize(cameraController.resize(width, height));
    renderer.setSize(width, height);
    invalidate();
  };
  resize();
  const observer = new ResizeObserver(resize);
  observer.observe(host);

  async function load() {
    try {
      const gltf = await loader.load(modelUrl, () => onStatus("Đang giải mã model và texture…"));
      if (disposed) return;
      scene.add(gltf.scene);
      glbCameras = gltf.cameras;
      cameraController.fit(gltf.scene);
      invalidate();
      onStatus(null);
    } catch (error) {
      if (!disposed) onError(error);
    }
  }
  void load();
  renderer.setAnimationLoop(() => {
    const cameraChanged = controls.update();
    const highlightsChanged = timedHighlights.update(playbackTime);
    if (cameraChanged || highlightsChanged || needsRender) {
      renderer.render(scene, camera);
      needsRender = false;
    }
  });

  const pointerStart = new THREE.Vector2();
  const onPointerDown = (event: PointerEvent) => pointerStart.set(event.clientX, event.clientY);
  const onPointerUp = (event: PointerEvent) => {
    if (pointerStart.distanceTo(new THREE.Vector2(event.clientX, event.clientY)) > 6) return;
    const rect = renderer.domElement.getBoundingClientRect();
    const point = new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1);
    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(point, camera);
    highlights.pick(raycaster);
    invalidate();
  };
  renderer.domElement.addEventListener("pointerdown", onPointerDown);
  renderer.domElement.addEventListener("pointerup", onPointerUp);

  return {
    enterExplore(mode: ExploreMode) { explore.enter(mode); highlights.show(true); invalidate(); },
    resetExplore() { explore.reset(); invalidate(); },
    exitExplore() { explore.exit(); highlights.show(false); highlights.select(null); invalidate(); },
    getCameraPose: cameraController.snapshot,
    restoreCameraPose(pose: ReturnType<typeof cameraController.snapshot>) { cameraController.restore(pose); invalidate(); },
    applyCameraPreset(preset: HeritageCamera, zoom = false) {
      const applied = cameraController.applyPreset(preset, zoom);
      invalidate();
      return applied;
    },
    useGLBCamera(name: string) {
      const source = glbCameras.find((camera) => camera.name === name);
      if (!(source instanceof THREE.PerspectiveCamera)) return false;
      cameraController.useGLBCamera(source);
      invalidate();
      return true;
    },
    setInteractiveHighlights(items: HeritageInteractiveHighlight[]) { highlights.set(items); invalidate(); },
    selectHighlight(id: number | null) { highlights.select(id); invalidate(); },
    onHighlightSelect: highlights.subscribe,
    setSceneHighlights: (items: TimedSceneHighlight[]) => timedHighlights.set(items),
    setPlaybackTime: (seconds: number) => { playbackTime = seconds; },
    dispose() {
      disposed = true;
      observer.disconnect();
      renderer.setAnimationLoop(null);
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      highlights.dispose();
      timedHighlights.dispose();
      controls.dispose();
      loader.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    },
  };
}

export type TourEngine = ReturnType<typeof createTourEngine>;
