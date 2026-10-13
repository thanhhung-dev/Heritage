import * as THREE from "three";
import type { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { HeritageCamera } from "@/types/heritage";

export function toVector3(value: number[] | Record<string, number> | null) {
  if (!value) return null;
  const xyz = Array.isArray(value) ? value : [value.x, value.y, value.z];
  return xyz.length === 3 && xyz.every(Number.isFinite) ? new THREE.Vector3(...xyz) : null;
}

/** Ease-in-out mượt cho chuyển động camera giữa hai stop (kiểu CyArk Tapestry). */
const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

export function createCameraController(camera: THREE.PerspectiveCamera, controls: OrbitControls) {
  const snapshot = () => ({ position: camera.position.clone(), target: controls.target.clone(), up: camera.up.clone(), fov: camera.fov });
  let home = snapshot();
  let flight: {
    fromPosition: THREE.Vector3; fromTarget: THREE.Vector3; fromUp: THREE.Vector3; fromFov: number;
    toPosition: THREE.Vector3; toTarget: THREE.Vector3; toUp: THREE.Vector3; toFov: number;
    duration: number; elapsed: number;
  } | null = null;
  let timeline: {
    from: ReturnType<typeof snapshot>;
    to: ReturnType<typeof snapshot>;
    flySeconds: number;
    lastTime: number;
    settled: boolean;
  } | null = null;
  let polarCeiling = controls.maxPolarAngle;
  const scratch = new THREE.Vector3();
  const scratchTarget = new THREE.Vector3();
  const scratchUp = new THREE.Vector3();
  const scratchOffset = new THREE.Vector3();
  let drivingPose = false;
  const syncControls = () => {
    const position = camera.position.clone();
    const target = controls.target.clone();
    const rotation = camera.quaternion.clone();
    const damping = controls.enableDamping;
    controls.enableDamping = false;
    controls.update();
    camera.position.copy(position);
    controls.target.copy(target);
    camera.quaternion.copy(rotation);
    controls.enableDamping = damping;
  };
  const allowPose = (position: THREE.Vector3, target: THREE.Vector3) => {
    const distance = position.distanceTo(target);
    controls.minDistance = Math.min(controls.minDistance, distance);
    controls.maxDistance = Math.max(controls.maxDistance, distance);
    scratchOffset.copy(position).sub(target);
    const length = scratchOffset.length();
    if (length > 1e-6) {
      const phi = Math.acos(THREE.MathUtils.clamp(scratchOffset.y / length, -1, 1));
      polarCeiling = Math.max(polarCeiling, phi + 0.02);
    }
    controls.maxPolarAngle = polarCeiling;
  };
  const restore = (pose: ReturnType<typeof snapshot>, duration = 0) => {
    timeline = null;
    flight = null;
    if (duration > 0) {
      const current = snapshot();
      flight = {
        fromPosition: current.position, fromTarget: current.target, fromUp: current.up, fromFov: current.fov,
        toPosition: pose.position.clone(), toTarget: pose.target.clone(), toUp: pose.up.clone(), toFov: pose.fov,
        duration, elapsed: 0,
      };
      allowPose(current.position, current.target);
      allowPose(pose.position, pose.target);
      return;
    }
    allowPose(pose.position, pose.target);
    camera.position.copy(pose.position);
    controls.target.copy(pose.target);
    camera.up.copy(pose.up);
    camera.fov = pose.fov;
    camera.updateProjectionMatrix();
    camera.lookAt(controls.target);
    drivingPose = false;
    syncControls();
  };
  const applyPose = (position: THREE.Vector3, target: THREE.Vector3, fov: number, up: THREE.Vector3) => {
    allowPose(position, target);
    camera.position.copy(position);
    controls.target.copy(target);
    camera.up.copy(up);
    camera.lookAt(target);
    if (camera.fov !== fov) {
      camera.fov = fov;
      camera.updateProjectionMatrix();
    }
    drivingPose = true;
  };
  return {
    snapshot,
    restore,
    reset: (duration = 0) => restore(home, duration),
    isFlying: () => flight !== null,
    startTimeline(preset: HeritageCamera, narrationSeconds: number) {
      const fromPosition = toVector3(preset.start_position);
      const fromTarget = toVector3(preset.start_target);
      const toPosition = toVector3(preset.zoom_position);
      const toTarget = toVector3(preset.zoom_target);
      if (!fromPosition || !fromTarget) return false;
      const from = { position: fromPosition, target: fromTarget, up: new THREE.Vector3(0, 1, 0), fov: camera.fov };
      timeline = null;
      if (!flight) restore(from);
      if (!toPosition || !toTarget) return false;
      if (!Number.isFinite(narrationSeconds) || narrationSeconds <= 0) return false;
      const to = { position: toPosition, target: toTarget, up: new THREE.Vector3(0, 1, 0), fov: camera.fov };
      allowPose(to.position, to.target);
      if (flight) {
        const current = snapshot();
        flight.fromPosition = current.position;
        flight.fromTarget = current.target;
        flight.fromUp = current.up;
        flight.fromFov = current.fov;
        flight.duration -= flight.elapsed;
        flight.elapsed = 0;
      }
      timeline = {
        from,
        to,
        flySeconds: narrationSeconds,
        lastTime: Number.NaN,
        settled: false,
      };
      return true;
    },
    updateTimeline(seconds: number) {
      if (!timeline) return false;
      if (!flight && seconds === timeline.lastTime) return false;
      const t = THREE.MathUtils.clamp(seconds / timeline.flySeconds, 0, 1);
      if (!flight && timeline.settled && t >= 1) return false;
      timeline.settled = !flight && t >= 1;
      timeline.lastTime = flight ? Number.NaN : seconds;
      const k = t;
      const position = scratch.copy(timeline.from.position).lerp(timeline.to.position, k);
      const target = scratchTarget.copy(timeline.from.target).lerp(timeline.to.target, k);
      const up = scratchUp.copy(timeline.from.up).lerp(timeline.to.up, k);
      let fov = timeline.from.fov + (timeline.to.fov - timeline.from.fov) * k;
      if (flight) {
        const blend = easeInOutCubic(Math.min(1, flight.elapsed / flight.duration));
        position.lerp(flight.fromPosition, 1 - blend);
        target.lerp(flight.fromTarget, 1 - blend);
        up.lerp(flight.fromUp, 1 - blend);
        fov = flight.fromFov + (fov - flight.fromFov) * blend;
      }
      applyPose(position, target, fov, up);
      if (timeline.settled) {
        drivingPose = false;
        syncControls();
      }
      return true;
    },
    stopTimeline() {
      timeline = null;
      flight = null;
      drivingPose = false;
      syncControls();
    },
    /** Có đang chạy chế độ camera bám timeline hay không. */
    hasTimeline: () => timeline !== null,
    /**
     * Bay camera tới preset trong `duration` giây. `duration <= 0` (instant_move)
     * thì đặt ngay. Trả về false nếu thiếu toạ độ hợp lệ.
     */
    flyToPreset(preset: HeritageCamera, zoom = false, duration = 1.6) {
      // Bay tự do và bay theo timeline loại trừ nhau: cái sau ghi đè cái trước.
      timeline = null;
      const position = toVector3(zoom ? preset.zoom_position : preset.start_position);
      const target = toVector3(zoom ? preset.zoom_target : preset.start_target);
      if (!position || !target) return false;
      const to = { position, target, up: new THREE.Vector3(0, 1, 0), fov: camera.fov };
      restore(to, duration);
      return true;
    },
    /**
     * Tiến trình bay theo `delta` giây. Trả về true khi pose vừa đổi (cần vẽ lại).
     * Caller gọi mỗi frame từ animation loop.
     */
    update(delta: number) {
      if (!flight) return false;
      flight.elapsed += delta;
      const t = Math.min(1, flight.elapsed / flight.duration);
      const k = easeInOutCubic(t);
      // Tái dùng vector tạm: đường này chạy mỗi frame nên không được cấp phát mới.
      const position = scratch.copy(flight.fromPosition).lerp(flight.toPosition, k);
      const target = scratchTarget.copy(flight.fromTarget).lerp(flight.toTarget, k);
      const up = scratchUp.copy(flight.fromUp).lerp(flight.toUp, k);
      const fov = flight.fromFov + (flight.toFov - flight.fromFov) * k;
      applyPose(position, target, fov, up);
      if (t >= 1) {
        flight = null;
        // Hết chuyến: trả quyền cho OrbitControls, đồng bộ một lần duy nhất.
        drivingPose = false;
        syncControls();
      }
      return true;
    },
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
      controls.maxPolarAngle = polarCeiling;
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
      // Đặt pose thủ công (focus marker) phải thắng timeline, nếu không
      // frame kế tiếp timeline sẽ kéo camera về quỹ đạo của nó.
      flight = null;
      timeline = null;
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
