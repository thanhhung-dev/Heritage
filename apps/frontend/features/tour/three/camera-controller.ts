import * as THREE from "three";
import type { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { HeritageCamera } from "@/types/heritage";

export function toVector3(value: number[] | Record<string, number> | null) {
  if (!value) return null;
  const xyz = Array.isArray(value) ? value : [value.x, value.y, value.z];
  return xyz.length === 3 && xyz.every(Number.isFinite) ? new THREE.Vector3(...xyz) : null;
}

export function createCameraController(camera: THREE.PerspectiveCamera, controls: OrbitControls) {
  const snapshot = () => ({ position: camera.position.clone(), target: controls.target.clone(), up: camera.up.clone(), fov: camera.fov });
  let home = snapshot();
  const restore = (pose: ReturnType<typeof snapshot>) => {
    // Xả quán tính trước khi reset, tránh damping kéo camera ra khỏi preset.
    const damping = controls.enableDamping;
    controls.enableDamping = false;
    controls.update();
    controls.enableDamping = damping;
    camera.position.copy(pose.position);
    controls.target.copy(pose.target);
    camera.up.copy(pose.up);
    camera.fov = pose.fov;
    camera.updateProjectionMatrix();
    // Preset tác giả không được bị giới hạn orbit của góc fit tự động cắt mất.
    const maxPolarAngle = controls.maxPolarAngle;
    const distance = pose.position.distanceTo(pose.target);
    controls.minDistance = Math.min(controls.minDistance, distance);
    controls.maxDistance = Math.max(controls.maxDistance, distance);
    controls.maxPolarAngle = Math.PI;
    controls.update();
    controls.maxPolarAngle = Math.max(maxPolarAngle, controls.getPolarAngle());
  };
  return {
    snapshot,
    restore,
    reset: () => restore(home),
    fit(model: THREE.Object3D) {
      model.updateWorldMatrix(true, true);
      const sphere = new THREE.Box3().setFromObject(model).getBoundingSphere(new THREE.Sphere());
      const verticalFov = THREE.MathUtils.degToRad(camera.fov);
      const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect);
      const distance = sphere.radius / Math.sin(Math.min(verticalFov, horizontalFov) / 2) * 1.15;
      controls.target.copy(sphere.center);
      camera.position.copy(sphere.center).addScaledVector(new THREE.Vector3(1, 0.8, 1).normalize(), distance);
      camera.near = Math.max(sphere.radius / 1000, 0.01);
      camera.far = distance + sphere.radius * 100;
      controls.minDistance = sphere.radius * 0.05;
      controls.maxDistance = distance * 5;
      camera.updateProjectionMatrix();
      controls.update();
      home = snapshot();
    },
    resize(width: number, height: number) {
      const halfFov = () => Math.min(THREE.MathUtils.degToRad(camera.fov) / 2,
        Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * camera.aspect));
      const oldHalfFov = halfFov();
      camera.aspect = width / height;
      const ratio = Math.sin(oldHalfFov) / Math.sin(halfFov());
      camera.position.sub(controls.target).multiplyScalar(ratio).add(controls.target);
      controls.minDistance *= ratio;
      controls.maxDistance *= ratio;
      // Preset reset cũng phải thích ứng với viewport mới.
      home.position.sub(home.target).multiplyScalar(ratio).add(home.target);
      camera.updateProjectionMatrix();
      return ratio;
    },
    applyPreset(preset: HeritageCamera, zoom = false) {
      const position = toVector3(zoom ? preset.zoom_position : preset.start_position);
      const target = toVector3(zoom ? preset.zoom_target : preset.start_target);
      if (!position || !target) return false;
      restore({ position, target, up: new THREE.Vector3(0, 1, 0), fov: camera.fov });
      return true;
    },
    useGLBCamera(source: THREE.Camera) {
      source.updateWorldMatrix(true, false);
      const position = source.getWorldPosition(new THREE.Vector3());
      const target = position.clone().add(source.getWorldDirection(new THREE.Vector3()));
      const up = new THREE.Vector3(0, 1, 0).applyQuaternion(source.getWorldQuaternion(new THREE.Quaternion()));
      restore({ position, target, up, fov: source instanceof THREE.PerspectiveCamera ? source.fov : camera.fov });
    },
  };
}

export type CameraController = ReturnType<typeof createCameraController>;
