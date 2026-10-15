import * as THREE from "three";
import type { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { ExploreArea } from "@/types/heritage";
import type { CameraController } from "./camera-controller";
import { clampPointToExploreArea, type ExploreBoundary } from "./explore-area";
import {
  createWalkInput,
  TURN_SPEED_DEG_PER_SECOND,
  WALK_SPEED,
} from "./walk-controls";
import { camLog, camWarn } from "./camera-debug";

export type ExploreMode = "standard" | "free" | "walk";

const LOOK_AHEAD = 1;

export interface WalkDeps {
  camera: THREE.PerspectiveCamera;
  canvas: HTMLElement;
  boundary: ExploreBoundary;
}

export function createExploreController(
  cameraController: CameraController,
  controls: OrbitControls,
  walkDeps?: WalkDeps,
) {
  let entry: ReturnType<CameraController["snapshot"]> | null = null;
  let entryMaxPolarAngle = controls.maxPolarAngle;
  let entryRotate = controls.enableRotate;
  let entryPan = controls.enablePan;
  let entryZoom = controls.enableZoom;

  const input = walkDeps ? createWalkInput(walkDeps.canvas) : null;
  const forward = new THREE.Vector3();
  const right = new THREE.Vector3();
  const move = new THREE.Vector3();
  const yAxis = new THREE.Vector3(0, 1, 0);

  let walk: { eyeHeight: number; area: ExploreArea | null } | null = null;
  let walkEntryEyeHeight = 0;
  let boundaryVisible = false;

  let area: ExploreArea | null = null;

  const stopWalk = () => {
    if (!walk) return;
    walk = null;
    boundaryVisible = false;
    input?.detach();
    controls.enableRotate = entryRotate;
    controls.enablePan = entryPan;
    controls.enableZoom = entryZoom;
    walkDeps?.boundary.show(false);
  };


  const refreshBoundary = (camera: THREE.PerspectiveCamera) => {
    const visible = walkDeps!.boundary.update(camera, walk!.area);
    const changed = visible !== boundaryVisible;
    boundaryVisible = visible;
    return changed;
  };

  return {
    setArea(next: ExploreArea | null) {
      area = next;
      if (walk) walk.area = next;
    },

    isWalking: () => walk !== null,

    enter(mode: ExploreMode, eyeHeight?: number) {
      if (!entry) {
        entry = cameraController.snapshot();
        entryMaxPolarAngle = controls.maxPolarAngle;
        entryRotate = controls.enableRotate;
        entryPan = controls.enablePan;
        entryZoom = controls.enableZoom;
      }

      if (mode === "walk") {
        if (!walkDeps || !input) {
          camWarn(
            "walk",
            "thiếu camera/canvas cho chế độ đi bộ ⇒ lùi về orbit tự do",
          );
        } else {
          stopWalk();
          
          const resolvedEyeHeight =
            typeof eyeHeight === "number" && Number.isFinite(eyeHeight)
              ? eyeHeight
              : walkDeps.camera.position.y;
          walkEntryEyeHeight = resolvedEyeHeight;
          walk = { eyeHeight: resolvedEyeHeight, area };
          input.attach();
          input.clear();
         
          controls.enableRotate = false;
          controls.enablePan = false;
          controls.enableZoom = false;
          controls.maxPolarAngle = Math.PI;
        
          boundaryVisible = false;
          camLog(
            "walk",
            `vào chế độ đi bộ · mắt y=${resolvedEyeHeight.toFixed(3)} · ${area ? `hộp ${area.extents.map((n) => (n * 2).toFixed(1)).join("×")}` : "KHÔNG có explore_area ⇒ chỉ khoá độ cao, không kẹp biên"}`,
          );
          return;
        }
      }

      stopWalk();
      controls.maxPolarAngle =
        mode === "free" ? Math.PI : Math.max(Math.PI / 2, controls.getPolarAngle());
    },

    reset(duration = 0) {
      input?.clear();
      if (walk) walk.eyeHeight = walkEntryEyeHeight;
      if (entry) cameraController.restore(entry, duration);
      else cameraController.reset(duration);
    },

    resize(ratio: number) {
      if (entry) entry.position.sub(entry.target).multiplyScalar(ratio).add(entry.target);
    },

    exit(duration = 0) {
      stopWalk();
      if (entry) {
        cameraController.restore(entry, duration);
        controls.maxPolarAngle = entryMaxPolarAngle;
        entry = null;
      }
    },
    updateWalk(delta: number): boolean {
      if (!walk || !walkDeps || !input) return false;
      if (cameraController.isFlying()) return false;

      const threeCamera = walkDeps.camera;
      const { forward: forwardAmount, strafe, turn } = input.read();

      let moved = false;
      if (turn !== 0) {
        const yaw = -turn * THREE.MathUtils.degToRad(TURN_SPEED_DEG_PER_SECOND) * delta;
        threeCamera.rotateOnWorldAxis(yAxis, yaw);
        moved = true;
      }

      if (forwardAmount !== 0 || strafe !== 0) {
        threeCamera.getWorldDirection(forward);
       
        forward.y = 0;
        if (forward.lengthSq() < 1e-8) forward.set(0, 0, -1);
        forward.normalize();
        right.crossVectors(forward, yAxis).normalize();

        move
          .set(0, 0, 0)
          .addScaledVector(forward, forwardAmount)
          .addScaledVector(right, strafe);

        if (move.lengthSq() > 0) {
          // Chuẩn hoá để đi chéo không nhanh gấp đôi.
          const amount = Math.min(move.length(), 1);
          move.normalize().multiplyScalar(WALK_SPEED * amount * delta);
          threeCamera.position.add(move);
          moved = true;
        }
      }

      if (walk.area && clampPointToExploreArea(threeCamera.position, walk.area)) {
        moved = true;
      }
      if (threeCamera.position.y !== walk.eyeHeight) {
        threeCamera.position.y = walk.eyeHeight;
        moved = true;
      }


      const wallChanged = refreshBoundary(threeCamera);

      if (!moved) return wallChanged;

      threeCamera.up.copy(yAxis);
      threeCamera.getWorldDirection(forward);
      controls.target.copy(threeCamera.position).addScaledVector(forward, LOOK_AHEAD);
      return true;
    },
  };
}
