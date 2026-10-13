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
  // Giới hạn mặc định khi người dùng tự orbit. CameraController sẽ NỚI giá trị này
  // khi áp preset tác giả nằm dưới mặt phẳng ngang (polar > 90°), nên đặt trước khi
  // khởi tạo controller để controller lấy đây làm trần gốc.
  controls.maxPolarAngle = Math.PI / 2;
  const cameraController = createCameraController(camera, controls);
  const explore = createExploreController(cameraController, controls);
  const loader = createModelLoader(renderer);
  const highlights = createInteractiveHighlights(scene);
  let needsRender = true;
  const invalidate = () => { needsRender = true; };
  const timedHighlights = createSceneHighlights(scene, loader, invalidate);
  /**
   * Thời gian phát của narration (giây) mà engine tự tiến mỗi frame trong lúc
   * audio đang chạy. React chỉ báo `currentTime` theo sự kiện `timeupdate` (~4Hz)
   * nên nếu bám thẳng giá trị đó thì mọi thứ theo thời gian — camera, highlight —
   * sẽ giật. Engine nội suy giữa hai lần React báo để mọi thứ mượt ở 60fps, và
   * đồng bộ lại khi có giá trị mới (kể cả khi người dùng seek).
   */
  let playbackTime = 0;
  let playbackClock = 0;
  let playbackSynced = 0;
  let playbackPlaying = false;
  /** Đồng bộ mốc thời gian từ React: đặt lại clock nội bộ. */
  const syncPlayback = () => { playbackClock = playbackTime; playbackSynced = playbackTime; };
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
  const clock = new THREE.Clock();
  renderer.setAnimationLoop(() => {
    // Delta thời gian cho tween camera; kẹp lại tránh nhảy khi tab bị treo.
    const delta = Math.min(clock.getDelta(), 0.1);
    // Tiến đồng hồ phát nội bộ khi audio đang chạy, để camera/highlight mượt 60fps
    // thay vì giật theo nhịp `timeupdate` (~4Hz) của thẻ audio.
    if (playbackPlaying) playbackClock += delta;
    const cameraFlying = cameraController.update(delta);
    // Chuyển động bám timeline narration (chỉ chạy khi không có chuyến bay chuyển cảnh).
    const timelineMoved = cameraController.updateTimeline(playbackClock);
    // `controls.update()` là hàm nặng (dựng lại spherical + lookAt). Khi controller
    // đang tự ghi pose thì nó không có gì để tính — bỏ hẳn, chỉ chạy lại lúc rảnh.
    const cameraDriven = cameraFlying || timelineMoved;
    const cameraChanged = cameraDriven ? false : controls.update();
    const highlightsChanged = timedHighlights.update(playbackClock);
    if (cameraDriven || cameraChanged || highlightsChanged || needsRender) {
      highlights.update(camera);
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
    resetExplore(duration = 0) { explore.reset(duration); invalidate(); },
    exitExplore(duration = 0) { explore.exit(duration); highlights.show(false); highlights.select(null); invalidate(); },
    getCameraPose: cameraController.snapshot,
    restoreCameraPose(pose: ReturnType<typeof cameraController.snapshot>, duration = 0) { cameraController.restore(pose, duration); invalidate(); },
    applyCameraPreset(preset: HeritageCamera, zoom = false) {
      const applied = cameraController.applyPreset(preset, zoom);
      invalidate();
      return applied;
    },
    /** Bay camera mượt tới preset trong `duration` giây (0 = đặt ngay). */
    flyCameraPreset(preset: HeritageCamera, zoom = false, duration = 1.6) {
      const applied = cameraController.flyToPreset(preset, zoom, duration);
      invalidate();
      return applied;
    },
    /**
     * Bật camera bám timeline narration cho cảnh hiện tại: đặt về pose start rồi
     * nội suy sang pose zoom theo tiến độ phát. `duration` là tổng thời lượng
     * clip narration (giây).
     */
    startCameraTimeline(preset: HeritageCamera, duration: number) {
      const started = cameraController.startTimeline(preset, duration);
      invalidate();
      return started;
    },
    /** Tắt camera bám timeline (chuyển cảnh, vào Explore, hoặc đặt pose thủ công). */
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
    setInteractiveHighlights(items: HeritageInteractiveHighlight[]) { highlights.set(items); invalidate(); },
    selectHighlight(id: number | null) { highlights.select(id); invalidate(); },
    onHighlightSelect: highlights.subscribe,
    setSceneHighlights: (items: TimedSceneHighlight[]) => timedHighlights.set(items),
    /**
     * Đồng bộ thời gian phát từ React. `playing` quyết định đồng hồ nội bộ có tự
     * tiến giữa các frame hay không; mọi lần gọi đều reset clock về đúng giá trị
     * này nên seek/tua cũng được phản ánh ngay.
     */
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
