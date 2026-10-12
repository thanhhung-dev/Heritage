import type { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { CameraController } from "./camera-controller";

export type ExploreMode = "standard" | "free";

/** Free cơ bản là orbit tự do; chưa phải đi bộ/FPS hay collision với explore_area. */
export function createExploreController(camera: CameraController, controls: OrbitControls) {
  let entry: ReturnType<CameraController["snapshot"]> | null = null;
  let entryMaxPolarAngle = controls.maxPolarAngle;
  return {
    enter(mode: ExploreMode) {
      if (!entry) {
        entry = camera.snapshot();
        entryMaxPolarAngle = controls.maxPolarAngle;
      }
      controls.maxPolarAngle = mode === "free" ? Math.PI : Math.max(Math.PI / 2, controls.getPolarAngle());
    },
    reset() {
      if (entry) camera.restore(entry);
      else camera.reset();
    },
    resize(ratio: number) {
      if (entry) entry.position.sub(entry.target).multiplyScalar(ratio).add(entry.target);
    },
    exit() {
      if (entry) {
        camera.restore(entry);
        controls.maxPolarAngle = entryMaxPolarAngle;
        entry = null;
      }
    },
  };
}
