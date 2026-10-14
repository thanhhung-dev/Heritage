import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type {
  HeritageCamera,
  HeritageInteractiveHighlight,
} from "@/types/heritage";
import { setupEnvironment } from "./environment";
import { createModelLoader } from "./model-loader";
import { createCameraController } from "./camera-controller";
import {
  createExploreController,
  type ExploreMode,
} from "./explore-controller";
import { createInteractiveHighlights } from "./interactive-highlights";
import { camLog, camWarn, cameraDebugEnabled, fmtVec } from "./camera-debug";
import {
  createSceneHighlights,
  type TimedSceneHighlight,
} from "./scene-highlights";

/** Ngưỡng di chuyển con trỏ (NDC) để coi là "di chuyển thật", không phải rung. */
export const HOVER_POINTER_EPSILON = 0.02;

/**
 * Có nên đánh giá lại hover theo con trỏ ở frame này không.
 *
 * Hai lý do phải chặn:
 * - Camera đang bay tới badge ⇒ badge trượt trên màn hình, raycast không đáng tin;
 *   đánh giá lúc này sẽ hủy chuyến bay giữa chừng và gây dao động vào/ra liên tục.
 * - Con trỏ chỉ rung vài pixel ⇒ coi như đứng yên, không đổi trạng thái hover.
 */
export function shouldEvaluateHover(
  pointer: { x: number; y: number },
  lastPointer: { x: number; y: number },
  approaching: boolean,
  epsilon = HOVER_POINTER_EPSILON,
) {
  if (approaching) return false;
  if (Number.isNaN(lastPointer.x)) return true;
  return Math.hypot(pointer.x - lastPointer.x, pointer.y - lastPointer.y) >= epsilon;
}

export function createTourEngine(
  host: HTMLDivElement,
  modelUrl: string,
  onStatus: (message: string | null) => void,
  onError: (error: unknown) => void,
) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  renderer.domElement.setAttribute(
    "aria-label",
    "Model 3D — kéo để xoay, cuộn để zoom",
  );
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
  const highlights = createInteractiveHighlights(
    scene,
    renderer.domElement,
    // Con trỏ vào badge ⇒ bay tới đứng trước badge; rời ra ⇒ bay về đúng pose cũ.
    (target) => cameraController.setDollyTarget(target),
  );
  // Chuyến bay hover phải nhường ngay khi người dùng kéo chuột.
  const detachPointerState = cameraController.attachPointerListeners(renderer.domElement);

  let needsRender = true;
  const invalidate = () => {
    needsRender = true;
  };

  const timedHighlights = createSceneHighlights(scene, loader, invalidate);

  let playbackTime = 0;
  let playbackClock = 0;
  let playbackSynced = 0;
  let playbackPlaying = false;

  const syncPlayback = () => {
    playbackClock = playbackTime;
    playbackSynced = playbackTime;
  };

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
      const gltf = await loader.load(modelUrl, () =>
        onStatus("Đang giải mã model và texture…"),
      );
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

  const clock = new THREE.Clock();
  let lastDebugAt = 0;
  let lastWriter = "";

  if (typeof window !== "undefined" && cameraDebugEnabled()) {
    (window as unknown as { __tourCameraDump?: () => unknown }).__tourCameraDump = () => {
      const state = { ...cameraController.debugState(), hoveredBadge: highlights.hoveredId() };
      console.log("%c[cam:dump]%c trạng thái camera hiện tại", "color:#185FA5;font-weight:600", "", state);
      return state;
    };
    camLog(
      "ready",
      'log chẩn đoán BẬT · tắt: window.__tourCameraDebug = false · dump: window.__tourCameraDump()',
    );
  }

  renderer.setAnimationLoop(() => {
    const delta = Math.min(clock.getDelta(), 0.1);

    if (playbackPlaying) playbackClock += delta;

    const cameraFlying = cameraController.update(delta);
    const dollyMoved = cameraController.updateDolly(delta);
    const timelineMoved = cameraController.updateTimeline(playbackClock);
    const cameraDriven = cameraFlying || dollyMoved || timelineMoved;
    // `dollyMoved` cũng là pose do controller ghi: bỏ `controls.update()` trong frame
    // đó, nếu không OrbitControls chạy chồng lên chuyến bay hover.
    const cameraChanged = cameraDriven ? false : controls.update();
    // Ăn pose mà OrbitControls vừa tính (damping, quay tay) để frame sau không giật
    // về pose cũ khi camera đang/đã dí gần badge.
    cameraController.syncPose();
    const highlightsChanged = timedHighlights.update(playbackClock);

    if (cameraDebugEnabled() && (cameraDriven || cameraChanged)) {
      // Hai nguồn cùng ghi pose trong một frame ⇒ chắc chắn giật.
      if (dollyMoved && timelineMoved) {
        camWarn("conflict", "dolly VÀ timeline cùng ghi pose trong một frame");
      }
      if (cameraFlying && dollyMoved) {
        camWarn("conflict", "flight VÀ dolly cùng ghi pose trong một frame (chuyến bay chuyển cảnh chưa nhường hover)");
      }
      // Thứ tự áp pose trong frame là flight → dolly → timeline, nên nguồn ghi CUỐI
      // CÙNG mới là cái đang điều khiển camera. Log phải phản ánh đúng thứ tự đó.
      const writer = timelineMoved ? "timeline" : dollyMoved ? "dolly" : cameraFlying ? "flight" : "controls";
      const now = performance.now();
      // Log mỗi 250ms, hoặc ngay khi đổi nguồn ghi để thấy rõ lúc bàn giao.
      if (writer !== lastWriter || now - lastDebugAt > 250) {
        lastWriter = writer;
        lastDebugAt = now;
        const state = cameraController.debugState();
        camLog(
          "frame",
          `writer=${writer} · pos=${fmtVec(camera.position)} · tgt=${fmtVec(controls.target)} · up=${fmtVec(camera.up)} · dist=${camera.position.distanceTo(controls.target).toFixed(2)} · hovered=${highlights.hoveredId()} · approaching=${state.approaching} · dolly=${state.hasDolly} · timeline=${state.hasTimeline} · mouse=${state.mouseActive}`,
        );
      }
    }

    if (cameraDriven || cameraChanged || highlightsChanged || needsRender) {
      highlights.update(camera, delta);
      renderer.render(scene, camera);
      needsRender = false;
    }
  });

  const pointerStart = new THREE.Vector2();
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  /**
   * Vị trí con trỏ (NDC) tại lần raycast hover gần nhất. Rung chuột vài pixel
   * không tính là "di chuyển": nếu tính, camera vừa bay vào badge (badge trượt
   * khỏi con trỏ) sẽ bị raycast trượt và đảo chiều bay vào/ra liên tục.
   */
  const lastHoverPointer = new THREE.Vector2(Number.NaN, Number.NaN);
  let lastSkipLogAt = 0;

  const updateRaycaster = (event: PointerEvent) => {
    const rect = renderer.domElement.getBoundingClientRect();

    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -(((event.clientY - rect.top) / rect.height) * 2 - 1);

    raycaster.setFromCamera(pointer, camera);
  };

  const onPointerMove = (event: PointerEvent) => {
    updateRaycaster(event);
    // Chỉ đánh giá lại hover khi con trỏ THỰC SỰ di chuyển, và không đánh giá khi
    // camera đang bay tới badge — badge trượt trên màn hình nên raycast không đáng
    // tin, đánh giá lúc này sẽ hủy chuyến bay giữa chừng.
    const approaching = cameraController.isApproaching();
    if (shouldEvaluateHover(pointer, lastHoverPointer, approaching)) {
      lastHoverPointer.copy(pointer);
      highlights.hover(raycaster);
    } else if (approaching && performance.now() - lastSkipLogAt > 500) {
      lastSkipLogAt = performance.now();
      camLog("hover", "bỏ qua đánh giá hover: camera đang bay tới badge");
    }
    invalidate();
  };

  const onPointerDown = (event: PointerEvent) =>
    pointerStart.set(event.clientX, event.clientY);

  const onPointerUp = (event: PointerEvent) => {
    if (
      pointerStart.distanceTo(new THREE.Vector2(event.clientX, event.clientY)) >
      6
    )
      return;

    updateRaycaster(event);
    highlights.pick(raycaster);
    invalidate();
  };

  renderer.domElement.addEventListener("pointermove", onPointerMove);
  renderer.domElement.addEventListener("pointerdown", onPointerDown);
  renderer.domElement.addEventListener("pointerup", onPointerUp);

  return {
    enterExplore(mode: ExploreMode) {
      // Pose trước khi vào Explore là "góc về" khi người dùng bấm Reset.
      cameraController.adoptCurrentPose();
      explore.enter(mode);
      highlights.show(true);
      invalidate();
    },
    resetExplore(duration = 0) {
      cameraController.clearDollyTarget();
      explore.reset(duration);
      invalidate();
    },
    exitExplore(duration = 0) {
      // Không giữ chuyến dí đang dở: `explore.exit` cần toàn quyền ghi pose.
      cameraController.clearDollyTarget();
      explore.exit(duration);
      highlights.show(false);
      highlights.select(null);
      invalidate();
    },
    /** Ẩn/hiện badge; ẩn thì nhả luôn chuyến dí để không tiếp tục tiến sát. */
    showHighlights(visible: boolean) {
      highlights.show(visible);
      if (!visible) cameraController.clearDollyTarget();
      invalidate();
    },
    /** Bỏ chuyến dí gần và lấy pose hiện tại làm góc mới (trước khi đổi cảnh). */
    releaseHighlightDolly() {
      cameraController.releaseDolly();
      invalidate();
    },
    getCameraPose: cameraController.snapshot,
    restoreCameraPose(
      pose: ReturnType<typeof cameraController.snapshot>,
      duration = 0,
    ) {
      cameraController.restore(pose, duration);
      invalidate();
    },
    applyCameraPreset(preset: HeritageCamera, zoom = false) {
      const applied = cameraController.applyPreset(preset, zoom);
      invalidate();
      return applied;
    },
    flyCameraPreset(preset: HeritageCamera, zoom = false, duration = 1.6) {
      const applied = cameraController.flyToPreset(preset, zoom, duration);
      invalidate();
      return applied;
    },
    startCameraTimeline(preset: HeritageCamera, duration: number) {
      const started = cameraController.startTimeline(preset, duration);
      invalidate();
      return started;
    },
    stopCameraTimeline() {
      cameraController.stopTimeline();
      invalidate();
    },
    isCameraFlying: cameraController.isFlying,
    useGLBCamera(name: string) {
      const source = glbCameras.find((camera) => camera.name === name);
      if (!(source instanceof THREE.PerspectiveCamera)) return false;
      cameraController.useGLBCamera(source);
      invalidate();
      return true;
    },
    setInteractiveHighlights(items: HeritageInteractiveHighlight[]) {
      // Danh sách điểm đổi ⇒ chuyến dí cũ (nếu có) hết hiệu lực.
      cameraController.clearDollyTarget();
      highlights.set(items);
      invalidate();
    },
    selectHighlight(id: number | null) {
      highlights.select(id);
      invalidate();
    },
    onHighlightSelect: highlights.subscribe,
    setSceneHighlights: (items: TimedSceneHighlight[]) =>
      timedHighlights.set(items),
    setPlaybackTime: (seconds: number, playing = false) => {
      playbackTime = seconds;
      playbackClock = seconds;
      playbackSynced = seconds;
      playbackPlaying = playing;
    },
    dispose() {
      disposed = true;
      observer.disconnect();
      renderer.setAnimationLoop(null);
      renderer.domElement.removeEventListener("pointermove", onPointerMove);
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      detachPointerState();
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
