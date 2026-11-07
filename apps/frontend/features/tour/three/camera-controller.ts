import * as THREE from "three";
import type { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type { HeritageCamera } from "@/types/heritage";
import { camLog, camWarn, fmtVec } from "./camera-debug";

export function toVector3(value: number[] | Record<string, number> | null) {
  if (!value) return null;
  const xyz = Array.isArray(value) ? value : [value.x, value.y, value.z];
  return xyz.length === 3 && xyz.every(Number.isFinite) ? new THREE.Vector3(...xyz) : null;
}

const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

export interface DollyTarget {
  point: THREE.Vector3;
  approach: number;
  minDistance?: number;
}

export function createCameraController(camera: THREE.PerspectiveCamera, controls: OrbitControls) {
  const snapshot = () => ({ position: camera.position.clone(), target: controls.target.clone(), up: camera.up.clone(), fov: camera.fov });
  let home = snapshot();
  const adoptCurrentPose = () => {
    home = snapshot();
  };
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
  let fitMinDistance = controls.minDistance;
  let editing = false;
  const scratch = new THREE.Vector3();
  const scratchTarget = new THREE.Vector3();
  const scratchUp = new THREE.Vector3();
  const scratchOffset = new THREE.Vector3();
  const scratchDirection = new THREE.Vector3();
  const scratchUpStripped = new THREE.Vector3();
  const scratchToCamera = new THREE.Vector3();
  const upY = new THREE.Vector3(0, 1, 0);
  const hoverUp = new THREE.Vector3();
  let drivingPose = false;
  let dolly: {
    fromPosition: THREE.Vector3; fromTarget: THREE.Vector3; fromUp: THREE.Vector3; fromFov: number;
    toPosition: THREE.Vector3; toTarget: THREE.Vector3; toUp: THREE.Vector3; toFov: number;
    duration: number; elapsed: number; returning: boolean;
  } | null = null;
  let dollyTarget: DollyTarget | null = null;
  let dollyTargetKey: string | null = null;
  let hoverStart: ReturnType<typeof snapshot> | null = null;
  let dollyActive = false;
  /**
   * Đang trong một CHUỖI hover (hover badge này rồi sang badge kế tiếp mà chưa về hết
   * góc gốc). Có cờ này để khoảng cách dí gần luôn neo vào pose gốc của chuỗi thay vì
   * khoảng cách camera hiện tại — nếu không, `approach` là TỈ LỆ nên hover liên tiếp sẽ
   * nhân dồn `approach^n` và camera chui hẳn vào trong model.
   */
  let chainActive = false;
  let mouseActive = false;
  const onMouseStart = () => { mouseActive = true; };
  const onMouseEnd = () => { mouseActive = false; };
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
  /**
   * Sàn `minDistance` suy từ khoảng cách các pose TÁC GIẢ đặt (preset/timeline).
   * Không dùng bán kính model: model Petra có bán kính rất lớn (gồm cả địa hình xa)
   * trong khi pose chỉ ở ~28–78, lấy `sphere.radius * 0.05` làm sàn sẽ khiến
   * OrbitControls kéo camera VỌT RA XA ngay khi chuyến hover kết thúc.
   */
  const noteAuthoredDistance = (position: THREE.Vector3, target: THREE.Vector3) => {
    const distance = position.distanceTo(target);
    if (!Number.isFinite(distance) || distance <= 1e-6) return;
    const floor = distance * 0.5;
    if (floor < fitMinDistance) fitMinDistance = floor;
  };
  const restoreMinDistance = () => {
    // Bất biến của OrbitControls: minDistance ≤ |camera−target|. Nếu sàn LỚN HƠN
    // khoảng cách hiện tại, `controls.update()` sẽ kéo camera vọt ra xa tới đúng sàn
    // ngay frame sau — đây là lỗi "hover xong camera bay ra xa".
    const radius = camera.position.distanceTo(controls.target);
    if (!editing && fitMinDistance > radius) {
      camWarn(
        "minDistance",
        `sàn=${fitMinDistance.toFixed(2)} > khoảng cách camera=${radius.toFixed(2)} ⇒ hạ sàn để không bị kéo ra xa`,
      );
    }
    // Authoring needs close-up zoom even after restoring a numeric/captured pose.
    // Keep the tour's authored floor intact so leaving the editor restores it.
    const floor = Math.min(fitMinDistance, radius, editing ? camera.near * 2 : Infinity);
    if (controls.minDistance !== floor) controls.minDistance = floor;
  };
  const restore = (pose: ReturnType<typeof snapshot>, duration = 0) => {
    timeline = null;
    flight = null;
    dolly = null;
    dollyActive = false;
    dollyTarget = null;
    dollyTargetKey = null;
    chainActive = false;
    hoverStart = null;
    restoreMinDistance();
    if (duration > 0) {
      const current = snapshot();
      flight = {
        fromPosition: current.position, fromTarget: current.target, fromUp: current.up, fromFov: current.fov,
        toPosition: pose.position.clone(), toTarget: pose.target.clone(), toUp: pose.up.clone(), toFov: pose.fov,
        duration, elapsed: 0,
      };
      adoptCurrentPose();
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
    adoptCurrentPose();
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
  const startHoverFlight = (to: ReturnType<typeof snapshot>, duration: number, returning = false) => {
    const current = snapshot();
    dolly = {
      fromPosition: current.position, fromTarget: current.target, fromUp: current.up, fromFov: current.fov,
      toPosition: to.position, toTarget: to.target, toUp: to.up, toFov: to.fov,
      duration, elapsed: 0, returning,
    };
    controls.minDistance = Math.min(controls.minDistance, to.position.distanceTo(to.target));
    controls.maxDistance = Math.max(controls.maxDistance, current.position.distanceTo(current.target));
  };

  const zoomIntoBadge = (target: DollyTarget) => {
    // Khoảng cách neo vào pose GỐC của chuỗi hover, không phải vị trí camera hiện tại.
    // `approach` là tỉ lệ, nên nếu đo từ vị trí đang dí sát badge trước thì mỗi lần
    // hover tiếp theo lại nhân thêm `approach` ⇒ cộng dồn zoom tới mức chui vào model.
    const anchor = hoverStart ? hoverStart.position : camera.position;
    const distance = anchor.distanceTo(target.point);
    scratchDirection.copy(camera.position).sub(target.point).setY(0);
    if (scratchDirection.lengthSq() < 1e-8) scratchDirection.copy(camera.getWorldDirection(scratchToCamera)).setY(0);
    if (scratchDirection.lengthSq() < 1e-8) scratchDirection.set(0, 0, 1);
    scratchDirection.normalize();
    const rise = THREE.MathUtils.clamp(0.3, 0, 0.45);
    hoverUp.copy(upY);
    scratchUpStripped.copy(scratchDirection).addScaledVector(hoverUp, Math.tan(rise)).normalize();
    const approach = Math.max(target.approach, 0.05);
    // Sàn hiệu dụng: sàn khai báo của badge + sàn "không để mặt phẳng cắt gần xén mất
    // badge". Badge là quad billboard nằm đúng ở khoảng cách này, nên chỉ cần gần hơn
    // `camera.near` là cả quad bị xén và badge "biến mất" khỏi màn hình.
    const floor = Math.max(target.minDistance ?? 0, camera.near * 2);
    let reach = distance * approach;
    if (reach < floor) {
      camLog(
        "dolly",
        `khoảng cách đích ${reach.toFixed(2)} < sàn ${floor.toFixed(2)} (near=${camera.near.toFixed(3)}) ⇒ nâng lên sàn để badge không bị xén`,
      );
      reach = floor;
    }
    const position = new THREE.Vector3().copy(target.point).addScaledVector(scratchUpStripped, reach);
    dollyActive = true;
    camLog(
      "dolly",
      `bay TỚI ${fmtVec(position)} · badge=${fmtVec(target.point)} · neo=${fmtVec(anchor)} · dist đích=${reach.toFixed(2)} · rise=${rise} · dist hiện tại=${camera.position.distanceTo(target.point).toFixed(2)}`,
    );
    startHoverFlight(
      { position, target: target.point.clone(), up: hoverUp.clone(), fov: camera.fov },
      0.9,
    );
  };
  /**
   * Chụp pose để quay về khi rời badge ("camera cũ", pattern entry/exit).
   *
   * Nếu đang có chuyến bay chuyển cảnh thì pose HIỆN TẠI chỉ là một điểm giữa đường.
   * Chụp nó làm "camera cũ" ⇒ rời badge xong camera dừng lơ lửng giữa không trung
   * thay vì về góc mặc định của deep live. Phải lấy ĐÍCH của chuyến bay, đồng thời
   * chuyến bay nhường quyền cho hover — nếu không, `update()` và `updateDolly()`
   * cùng ghi pose mỗi frame và `syncControls()` cuối chuyến bay bắn vào giữa chuyến hover.
   */
  const captureReturnPose = () => {
    if (!flight) return snapshot();
    const pose = {
      position: flight.toPosition.clone(),
      target: flight.toTarget.clone(),
      up: flight.toUp.clone(),
      fov: flight.toFov,
    };
    camLog(
      "hover",
      `chuyến bay chuyển cảnh đang dở ⇒ "camera cũ" lấy ĐÍCH ${fmtVec(pose.position)} (không lấy điểm giữa đường)`,
    );
    flight = null;
    syncControls();
    return pose;
  };
  /** Rời badge ⇒ bay về "camera cũ" đã chụp lúc bắt đầu hover (pattern entry/exit). */
  const returnToHoverStart = () => {
    const pose = hoverStart;
    dollyActive = false;
    if (!pose) {
      dolly = null;
      restoreMinDistance();
      return false;
    }
    startHoverFlight(
      { position: pose.position.clone(), target: pose.target.clone(), up: pose.up.clone(), fov: pose.fov },
      0.9,
      true,
    );
    return true;
  };
  return {
    snapshot,
    restore,
    adoptCurrentPose,
    enableEditing() {
      const previous = { enableZoom: controls.enableZoom, enablePan: controls.enablePan };
      editing = true;
      controls.enableZoom = true;
      controls.enablePan = true;
      restoreMinDistance();
      return () => {
        editing = false;
        Object.assign(controls, previous);
        restoreMinDistance();
      };
    },
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
      noteAuthoredDistance(from.position, from.target);
      noteAuthoredDistance(to.position, to.target);
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
      camLog("timeline", `start ${narrationSeconds.toFixed(1)}s · ${fmtVec(from.position)} → zoom ${fmtVec(to.position)}`);
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
        camLog("timeline", `settled tại ${fmtVec(timeline.to.position)}`);
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
      noteAuthoredDistance(position, target);
      restore(to, duration);
      return true;
    },
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
    setDollyTarget(target: DollyTarget | null) {
      const approaching = !!target && Number.isFinite(target.approach) && target.approach < 1
        && (target.point.x !== camera.position.x || target.point.y !== camera.position.y || target.point.z !== camera.position.z);
      if (approaching && target) {
        const targetKey = `${target.point.x},${target.point.y},${target.point.z}`;
        if (dollyTargetKey === targetKey && dollyActive) return false;
        dollyTarget = target;
        dollyTargetKey = targetKey;
        timeline = null;
        if (!chainActive || !hoverStart) {
          hoverStart = captureReturnPose();
          chainActive = true;
        } else {
          camLog(
            "hover",
            `nối tiếp chuỗi hover ⇒ giữ nguyên "camera cũ" ${fmtVec(hoverStart.position)} và mốc đo khoảng cách (không cộng dồn zoom)`,
          );
        }
        camLog(
          "hover",
          `IN badge ${fmtVec(target.point)} · "camera cũ" ${fmtVec(hoverStart.position)} · dist=${camera.position.distanceTo(target.point).toFixed(2)} · approach=${target.approach}`,
        );
        zoomIntoBadge(target);
        return true;
      }
      dollyTarget = null;
      dollyTargetKey = null;
      if (!dollyActive) return false;
      camLog("hover", `OUT badge → quay về "camera cũ" ${fmtVec(hoverStart?.position)}`);
      return returnToHoverStart();
    },
    setPointerActive(active: boolean) {
      mouseActive = active;
    },
    clearDollyTarget() {
      dollyTarget = null;
      dollyTargetKey = null;
      dolly = null;
      chainActive = false;
      hoverStart = null;
      restoreMinDistance();
      adoptCurrentPose();
    },
    hasDolly: () => dolly !== null,
    isApproaching: () => dollyActive && dolly !== null,
    /** Trạng thái để chẩn đoán qua `window.__tourCameraDump()`. */
    debugState() {
      return {
        writer: flight ? "flight" : dolly ? "dolly" : timeline ? "timeline" : "none",
        hasDolly: dolly !== null,
        dollyActive,
        approaching: dollyActive && dolly !== null,
        hasTimeline: timeline !== null,
        timelineSettled: timeline?.settled ?? false,
        mouseActive,
        dollyProgress: dolly ? Number(Math.min(1, dolly.elapsed / dolly.duration).toFixed(3)) : null,
        dollyReturning: dolly?.returning ?? null,
        chainActive,
        hoverStart: hoverStart ? hoverStart.position.toArray() : null,
        dollyTo: dolly ? dolly.toPosition.toArray() : null,
        camera: {
          position: camera.position.toArray(),
          target: controls.target.toArray(),
          up: camera.up.toArray(),
          fov: camera.fov,
          near: camera.near,
          far: camera.far,
        },
        minDistance: controls.minDistance,
        maxDistance: controls.maxDistance,
        fitMinDistance,
      };
    },
    updateDolly(delta: number) {
      if (!dolly) return false;
      dolly.elapsed += delta;
      const k = easeInOutCubic(Math.min(1, dolly.elapsed / dolly.duration));
      const position = scratch.copy(dolly.fromPosition).lerp(dolly.toPosition, k);
      const t = scratchTarget.copy(dolly.fromTarget).lerp(dolly.toTarget, k);
      applyPose(position, t, camera.fov, dolly.fromUp);
      if (k >= 1) {
        const donePosition = camera.position.clone();
        const returning = dolly.returning;
        dolly = null;
        // Chuyến bay VỀ kết thúc = camera đã ở lại góc gốc ⇒ chuỗi hover chấm dứt.
        // Lần hover sau sẽ neo khoảng cách vào góc mới này (không nối tiếp chuỗi cũ).
        if (returning) chainActive = false;
        drivingPose = false;
        restoreMinDistance();
        adoptCurrentPose();
        syncControls();
        camLog(
          "dolly",
          `${returning ? "VỀ" : "TỚI"} DONE tại ${fmtVec(donePosition)} · lệch target=${donePosition.distanceTo(controls.target).toFixed(2)} · min=${controls.minDistance.toFixed(2)} max=${controls.maxDistance.toFixed(2)} fitMin=${fitMinDistance.toFixed(2)} · chuỗi=${chainActive}`,
        );
      }
      return true;
    },
    syncPose() {
      if (!dolly || !mouseActive) return;
      camWarn("hover", "người dùng kéo chuột ⇒ hủy chuyến hover, pose hiện tại thành góc mới");
      dolly = null;
      dollyActive = false;
      dollyTarget = null;
      dollyTargetKey = null;
      // Góc hiện tại thành gốc mới ⇒ chuỗi hover cũ không còn ý nghĩa.
      chainActive = false;
      hoverStart = null;
      restoreMinDistance();
      adoptCurrentPose();
      syncControls();
    },
    releaseDolly() {
      dolly = null;
      dollyTarget = null;
      restoreMinDistance();
      return restore(snapshot());
    },
    fit(model: THREE.Object3D) {
      model.updateWorldMatrix(true, true);
      const fullSphere = new THREE.Box3().setFromObject(model).getBoundingSphere(new THREE.Sphere());

      // Terrain/backdrop có thể rộng hàng chục km. Nếu đưa nó vào khung ngắm,
      // camera lùi rất xa và công trình chỉ còn vài pixel. Chỉ đo các mesh không
      // được đánh dấu `ignoreFit`, nhưng vẫn dùng full bounds cho mặt phẳng cắt xa.
      const focusBox = new THREE.Box3();
      model.traverse((object) => {
        if (!(object instanceof THREE.Mesh)) return;
        let ignored = false;
        for (let current: THREE.Object3D | null = object; current; current = current.parent) {
          if (current.userData.ignoreFit === true) {
            ignored = true;
            break;
          }
        }
        if (!ignored) focusBox.expandByObject(object);
      });
      const sphere = focusBox.isEmpty()
        ? fullSphere
        : focusBox.getBoundingSphere(new THREE.Sphere());

      const verticalFov = THREE.MathUtils.degToRad(camera.fov);
      const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect);
      const distance = sphere.radius / Math.sin(Math.min(verticalFov, horizontalFov) / 2) * 1.15;
      controls.target.copy(sphere.center);
      camera.position.copy(sphere.center).addScaledVector(new THREE.Vector3(1, 0.8, 1).normalize(), distance);
      // `near` vẫn neo vào full bounds để giữ độ chính xác depth như trước; `far`
      // phải phủ cả backdrop dù camera đang ngắm riêng công trình.
      camera.near = Math.max(fullSphere.radius / 20000, 0.01);
      camera.far = Math.max(
        distance + sphere.radius * 2,
        camera.position.distanceTo(fullSphere.center) + fullSphere.radius * 1.25,
      );
      controls.minDistance = sphere.radius * 0.05;
      controls.maxDistance = distance * 5;
      camera.updateProjectionMatrix();
      controls.maxPolarAngle = polarCeiling;
      controls.update();
      // Trần minDistance mới của model; chuyến dí gần chỉ được nới trong lúc bay.
      fitMinDistance = controls.minDistance;
      camLog(
        "fit",
        `bán kính focus=${sphere.radius.toFixed(2)} full=${fullSphere.radius.toFixed(2)} · near=${camera.near.toFixed(3)} · far=${camera.far.toFixed(0)} · minDistance=${controls.minDistance.toFixed(2)} · maxDistance=${controls.maxDistance.toFixed(2)} · cameraDist=${camera.position.distanceTo(controls.target).toFixed(2)}`,
      );
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
      fitMinDistance *= ratio;
      camLog(
        "resize",
        `${width.toFixed(0)}×${height.toFixed(0)} · ratio=${ratio.toFixed(4)} · min=${controls.minDistance.toFixed(2)} max=${controls.maxDistance.toFixed(2)} fitMin=${fitMinDistance.toFixed(2)}`,
      );
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
      noteAuthoredDistance(position, target);
      restore({ position, target, up: new THREE.Vector3(0, 1, 0), fov: camera.fov });
      return true;
    },
    /**
     * Ghi pose do QUỸ ĐẠO CAMERA (clip trong GLB) tính ra.
     *
     * Khác `restore`: không tạo chuyến bay và không đụng `timeline` — hàm này
     * được gọi mỗi frame với thời gian audio, nên mọi hiệu ứng trung gian ở đây
     * đều thành nhiễu. Cùng đường ghi với `updateTimeline` (`applyPose`) để cờ
     * `drivingPose` vẫn đúng.
     */
    applyPathPose(position: THREE.Vector3, target: THREE.Vector3, fov: number) {
      noteAuthoredDistance(position, target);
      applyPose(position, target, fov, upY);
    },
    finishPathPose() {
      if (!drivingPose) return;
      drivingPose = false;
      syncControls();
    },
    /**
     * Đặt camera theo một camera NƯỚNG SẴN trong file GLB (`scene.camera_node_name`).
     *
     * Camera trong glTF chỉ có vị trí + hướng nhìn, còn OrbitControls cần một ĐIỂM
     * NGẮM (`target`) để quay quanh. Vì vậy `target` được truyền vào từ ngoài — nơi
     * biết model (node đích trong GLB, hoặc điểm tia chiếu trúng model). Không có
     * `target` thì lùi về điểm cách 1 m theo hướng nhìn: với model vài trăm mét,
     * quỹ đạo quay sẽ bám sát camera và rất khó dùng, nhưng vẫn hơn là không có gì.
     */
    useGLBCamera(source: THREE.Camera, target: THREE.Vector3 | null = null, duration = 0) {
      source.updateWorldMatrix(true, false);
      const position = source.getWorldPosition(new THREE.Vector3());
      const direction = source.getWorldDirection(new THREE.Vector3());
      const sourceUp = new THREE.Vector3(0, 1, 0).applyQuaternion(
        source.getWorldQuaternion(new THREE.Quaternion()),
      );
      // KHÔNG bê `up` của camera trong GLB vào: OrbitControls dựng hệ quay quanh
      // `camera.up`, nên một up nghiêng (camera có roll) sẽ làm cả quỹ đạo quay
      // lệch theo. Preset trong DB cũng luôn dùng (0, 1, 0) — giữ nhất quán.
      if (sourceUp.angleTo(upY) > 0.02) {
        camWarn("glb-cam", `camera GLB có roll ${THREE.MathUtils.radToDeg(sourceUp.angleTo(upY)).toFixed(1)}° ⇒ bỏ qua, dùng trục Y thế giới`);
      }
      const aim = target && target.distanceTo(position) > 1e-3
        ? target.clone()
        : position.clone().add(direction);
      const fov = source instanceof THREE.PerspectiveCamera ? source.fov : camera.fov;
      noteAuthoredDistance(position, aim);
      restore({ position, target: aim, up: upY.clone(), fov }, duration);
    },
    /**
     * Gắn tín hiệu "chuột đang được kéo" lên canvas của renderer. Nghe ở capture để
     * vẫn nhận được sự kiện khi OrbitControls nuốt/`stopPropagation`.
     * Trả về hàm gỡ đăng ký.
     */
    attachPointerListeners(element: HTMLElement) {
      const capture = { capture: true } as const;
      element.addEventListener("pointerdown", onMouseStart, capture);
      window.addEventListener("pointerup", onMouseEnd, capture);
      window.addEventListener("pointercancel", onMouseEnd, capture);
      return () => {
        element.removeEventListener("pointerdown", onMouseStart, capture);
        window.removeEventListener("pointerup", onMouseEnd, capture);
        window.removeEventListener("pointercancel", onMouseEnd, capture);
      };
    },
  };
}

export type CameraController = ReturnType<typeof createCameraController>;
