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
  // Trạng thái bay camera giữa hai preset. Khi đang bay, OrbitControls tạm khóa
  // để người dùng không kéo lệch hướng; xong thì mở lại.
  let flight: {
    fromPosition: THREE.Vector3; fromTarget: THREE.Vector3; fromUp: THREE.Vector3; fromFov: number;
    toPosition: THREE.Vector3; toTarget: THREE.Vector3; toUp: THREE.Vector3; toFov: number;
    duration: number; elapsed: number;
  } | null = null;
  /**
   * Chuyển động camera BÁM THEO TIMELINE narration: camera nội suy giữa pose
   * `start` và pose `zoom` theo tiến độ phát của clip, nên tua video (seek) là
   * camera nhảy tới đúng vị trí tương ứng. `null` khi cảnh không bật chế độ này
   * hoặc khi người dùng đang ở chế độ Explore (lúc đó trả quyền cho người dùng).
   */
  let timeline: {
    from: ReturnType<typeof snapshot>;
    to: ReturnType<typeof snapshot>;
    /** Giây: hết đoạn này camera đã tới hẳn pose `to`. */
    flySeconds: number;
    /** Vị trí đã áp ở lần cập nhật trước, để bỏ qua frame không đổi. */
    lastTime: number;
    /** Đã tới pose `to` chưa — khi rồi thì thôi áp pose mỗi frame. */
    settled: boolean;
  } | null = null;
  /**
   * Góc cực (polar) tối đa cho phép khi orbit. `OrbitControls` mặc định chặn
   * `maxPolarAngle = π/2` (không cho camera xuống dưới mặt phẳng ngang của target),
   * nhưng preset tác giả trong tour.json có cảnh đặt camera THẤP HƠN target
   * (polar > 90°). Nếu để clamp đó bật, `controls.update()` sẽ ép camera về đúng
   * mặt phẳng π/2 ở MỖI frame — camera "đứng im" dù tween vẫn chạy.
   * Vì vậy controller phải tự nới giới hạn này theo preset đã áp.
   */
  let polarCeiling = controls.maxPolarAngle;
  /**
   * Vector tạm dùng lại giữa các frame. Đường chạy mỗi frame (bay / timeline)
   * không được cấp phát Vector3 mới — mỗi `.clone()` là một object cho GC dọn,
   * ở 60fps sẽ tạo áp lực GC và làm khựng chuyển động.
   *
   * QUAN TRỌNG: mỗi mục đích phải có vector RIÊNG. Nếu `allowPose` dùng chung
   * vector với tham số `position` đang truyền vào thì nó sẽ ghi đè chính giá trị
   * đang cần dùng (aliasing), khiến pose áp sai.
   */
  const scratch = new THREE.Vector3();
  const scratchTarget = new THREE.Vector3();
  const scratchUp = new THREE.Vector3();
  /** Vector riêng cho `allowPose` — không được trùng với `scratch`/`scratchTarget`. */
  const scratchOffset = new THREE.Vector3();
  /**
   * Pose đang do controller tự quản (lúc bay / chạy timeline). Khi cờ này bật,
   * vòng lặp render KHÔNG gọi `controls.update()` nữa — vì `applyPose` đã ghi
   * thẳng position/target và OrbitControls không có gì để tính. Chỉ đồng bộ lại
   * OrbitControls một lần khi kết thúc (xem `syncControls`).
   */
  let drivingPose = false;
  /**
   * Đồng bộ trạng thái nội bộ của OrbitControls theo camera hiện tại rồi mới
   * giao lại quyền điều khiển cho người dùng. Gọi một lần khi kết thúc chuyến bay
   * hoặc timeline, KHÔNG gọi mỗi frame.
   */
  const syncControls = () => {
    const position = camera.position.clone();
    const target = controls.target.clone();
    const rotation = camera.quaternion.clone();
    const damping = controls.enableDamping;
    controls.enableDamping = false;
    controls.update();
    // update xóa quán tính cũ nhưng không được đẩy camera lệch khỏi pose vừa chốt.
    camera.position.copy(position);
    controls.target.copy(target);
    camera.quaternion.copy(rotation);
    controls.enableDamping = damping;
  };
  /** Nới trần polar để pose chỉ định luôn nằm trong vùng orbit hợp lệ. */
  const allowPose = (position: THREE.Vector3, target: THREE.Vector3) => {
    const distance = position.distanceTo(target);
    controls.minDistance = Math.min(controls.minDistance, distance);
    controls.maxDistance = Math.max(controls.maxDistance, distance);
    scratchOffset.copy(position).sub(target);
    const length = scratchOffset.length();
    if (length > 1e-6) {
      // Góc cực thực của pose = arccos(Δy / |offset|); cộng biên nhỏ tránh kẹp đúng rìa.
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
  /**
   * Ghi pose ở đường nhanh: chỉ copy vị trí/target và `lookAt`, KHÔNG chạy
   * `controls.update()` và KHÔNG cập nhật ma trận chiếu (fov không đổi giữa hai
   * pose của cùng một cảnh). Đây là đường chạy mỗi frame nên phải thật rẻ.
   */
  const applyPose = (position: THREE.Vector3, target: THREE.Vector3, fov: number, up: THREE.Vector3) => {
    allowPose(position, target);
    camera.position.copy(position);
    controls.target.copy(target);
    // `lookAt` suy ra hướng nhìn từ `camera.up`; phải đặt lại up mỗi frame vì
    // OrbitControls tự xoay up theo quỹ đạo. Bỏ bước này thì pose bị lệch.
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
    /** Đang bay camera giữa hai stop hay không. */
    isFlying: () => flight !== null,
    /**
     * Bật chuyển động camera bám timeline narration cho cảnh hiện tại.
     *
     * Camera được đặt ngay tại pose `start`, rồi nội suy dần sang pose `zoom`
     * theo tiến độ phát của clip (`updateTimeline`). `narrationSeconds` là tổng
     * thời lượng clip; không có (0/không xác định) thì giữ nguyên pose start và
     * trả về false. Trả về true nếu đã bật được chế độ timeline.
     */
    startTimeline(preset: HeritageCamera, narrationSeconds: number) {
      const fromPosition = toVector3(preset.start_position);
      const fromTarget = toVector3(preset.start_target);
      const toPosition = toVector3(preset.zoom_position);
      const toTarget = toVector3(preset.zoom_target);
      // Không có pose start thì không biết đặt camera ở đâu — bỏ qua hoàn toàn.
      if (!fromPosition || !fromTarget) return false;
      const from = { position: fromPosition, target: fromTarget, up: new THREE.Vector3(0, 1, 0), fov: camera.fov };
      // Metadata có thể đến giữa chuyến bay chuyển cảnh: giữ chuyến bay đó,
      // không nhảy thẳng về start. Khi không bay, đặt pose start như thường lệ.
      timeline = null;
      if (!flight) restore(from);
      // Thiếu pose zoom, hoặc clip quá ngắn / chưa biết thời lượng ⇒ đứng yên ở start.
      if (!toPosition || !toTarget) return false;
      if (!Number.isFinite(narrationSeconds) || narrationSeconds <= 0) return false;
      const to = { position: toPosition, target: toTarget, up: new THREE.Vector3(0, 1, 0), fov: camera.fov };
      allowPose(to.position, to.target);
      if (flight) {
        // Đổi đích từ start sang pose audio: lấy pose đang hiển thị làm gốc,
        // giữ thời gian còn lại để metadata đến muộn không gây bước nhảy.
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
    /**
     * Áp vị trí camera theo thời điểm phát hiện tại của narration.
     *
     * `seconds` là `currentTime` của audio — tua video là giá trị này nhảy nên
     * camera theo tới đúng chỗ, không chỉ tiến một chiều. Trả về true khi pose
     * thay đổi (cần vẽ lại). Caller gọi mỗi frame từ animation loop.
     */
    updateTimeline(seconds: number) {
      if (!timeline) return false;
      if (!flight && seconds === timeline.lastTime) return false;
      const t = THREE.MathUtils.clamp(seconds / timeline.flySeconds, 0, 1);
      // Đã tới đích VÀ thời gian không lùi lại ⇒ không cần áp lại pose mỗi frame,
      // tiết kiệm một lần lookAt/allowPose suốt phần còn lại của clip. Nếu người
      // dùng tua ngược về trong đoạn bay thì phải chạy lại, nếu không camera sẽ
      // đứng nguyên ở góc zoom dù video đã về đầu.
      if (!flight && timeline.settled && t >= 1) return false;
      timeline.settled = !flight && t >= 1;
      // Frame kết thúc chuyến bay vẫn phải áp timeline, kể cả audio đang pause.
      timeline.lastTime = flight ? Number.NaN : seconds;
      // Timeline đi đều suốt audio; easing chỉ dành cho chuyến bay chuyển cảnh.
      const k = t;
      // Tái dùng `scratch` cho vị trí/target để không cấp phát mỗi frame.
      // (Giá trị được `applyPose` copy vào camera ngay sau đây nên dùng lại an toàn.)
      const position = scratch.copy(timeline.from.position).lerp(timeline.to.position, k);
      const target = scratchTarget.copy(timeline.from.target).lerp(timeline.to.target, k);
      const up = scratchUp.copy(timeline.from.up).lerp(timeline.to.up, k);
      let fov = timeline.from.fov + (timeline.to.fov - timeline.from.fov) * k;
      if (flight) {
        // Nếu audio bắt đầu khi còn chuyển cảnh, hòa chuyến bay vào pose audio
        // hiện tại để không bị nhảy khi chuyến bay kết thúc.
        const blend = easeInOutCubic(Math.min(1, flight.elapsed / flight.duration));
        position.lerp(flight.fromPosition, 1 - blend);
        target.lerp(flight.fromTarget, 1 - blend);
        up.lerp(flight.fromUp, 1 - blend);
        fov = flight.fromFov + (fov - flight.fromFov) * blend;
      }
      applyPose(position, target, fov, up);
      // Vừa chốt pose cuối ⇒ trả quyền lại cho OrbitControls một lần duy nhất.
      if (timeline.settled) {
        drivingPose = false;
        syncControls();
      }
      return true;
    },
    /** Nhường quyền camera khi chuyển cảnh, chọn góc hoặc vào Explore. */
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
