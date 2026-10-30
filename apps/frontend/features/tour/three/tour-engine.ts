import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import type {
  ExploreArea,
  HeritageCamera,
  HeritageInteractiveHighlight,
  HeritageSkyPreset,
} from "@/types/heritage";
import { createEnvironment } from "./environment";
import { createModelLoader, type ModelProgress } from "./model-loader";
import { createCameraController } from "./camera-controller";
import { createCameraPath, type CameraPath } from "./camera-path";
import { createExploreBoundary } from "./explore-area";
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

export const HOVER_POINTER_EPSILON = 0.02;

/**
 * Trần tỉ lệ điểm ảnh. Model là lưới photogrammetry phủ kín màn hình nên chi phí
 * gần như tuyến tính theo SỐ PIXEL: màn 2x mà render 1.5x đã là 2.25 lần số pixel
 * so với CSS. 1.5 là mức còn phân biệt được với 1.0 trên ảnh tĩnh.
 */
const MAX_PIXEL_RATIO_CAP = 1.5;

/** Sàn tỉ lệ điểm ảnh — dưới mức này ảnh đã nhoè rõ, thà chấp nhận ít frame hơn. */
const MIN_PIXEL_RATIO = 0.8;

/** Bước hạ/nâng tỉ lệ điểm ảnh mỗi lần thích ứng. */
const PIXEL_RATIO_STEP = 0.2;

/** Số frame gom lại mới đánh giá một lần (đủ dài để bỏ qua dao động từng frame). */
const ADAPT_WINDOW = 40;

/** Ngưỡng hạ: trung bình > 24 ms/frame (dưới ~42 fps). */
const ADAPT_DOWN_SECONDS = 0.024;

/** Ngưỡng nâng: trung bình < 15 ms/frame (trên ~66 fps) mới dám thử lại. */
const ADAPT_UP_SECONDS = 0.015;

/** Số frame chờ sau mỗi lần đổi tỉ lệ trước khi đánh giá tiếp (chống dao động). */
const ADAPT_COOLDOWN = 60;


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

/**
 * Chuẩn hoá tên camera để so khớp: bỏ hết dấu phân cách và hạ chữ.
 * `Cam_S0`, `cam s0`, `CAM-S0`, `Camera_S0` → cùng một khoá.
 */
export function normalizeCameraName(name: string) {
  return name.trim().toLowerCase().replace(/[^a-z0-9]/g, "");
}

/**
 * Đầu vào cho `useGLBCameraForScene`: cảnh nào, trong tổng số bao nhiêu cảnh.
 *
 * `sequence` theo đúng quy ước DB (`-1` = overview, `0..N-1` = scene), `sceneCount`
 * là số cảnh nội dung (không tính overview) — dùng cho nhánh "GLB có đúng bằng số
 * cảnh thì lấy theo thứ tự node".
 */
export interface GLBCameraSceneSpec {
  sequence: number;
  sceneCount: number;
}

/** Các cách đặt tên được chấp nhận cho cảnh `sequence`. */
function cameraNameCandidates(sequence: number) {
  const names =
    sequence < 0
      ? ["Cam_Overview", "Camera_Overview", "Overview_Cam", "Overview_Camera"]
      : [
          `Cam_S${sequence}`,
          `Camera_S${sequence}`,
          `S${sequence}_Cam`,
          `S${sequence}_Camera`,
          `Camera_${sequence}`,
          `Camera${sequence}`,
          `Cam_${sequence}`,
          `Cam${sequence}`,
        ];
  return new Set(names.map(normalizeCameraName));
}

/**
 * Chọn camera trong GLB cho một cảnh — hàm thuần để test được không cần WebGL.
 *
 * Thứ tự:
 *  1. tên theo quy ước của cảnh (`Cam_S2`, `Camera_2`, `S2_Cam`…), không phân biệt
 *     hoa thường và dấu phân cách;
 *  2. nếu GLB có ĐÚNG bằng số cảnh thì lấy theo đúng thứ tự node — cách này để
 *     người dựng model không phải đổi tên gì, nhưng chỉ dùng khi số lượng khớp
 *     tuyệt đối, tránh chọn nhầm camera của cảnh khác;
 *  3. `-1` = không tìm được.
 */
export function pickGLBCamera(names: string[], sequence: number, sceneCount: number) {
  const candidates = cameraNameCandidates(sequence);
  const byName = names.findIndex((name) => candidates.has(normalizeCameraName(name)));
  if (byName >= 0) return byName;
  if (sceneCount === names.length && sequence >= 0 && sequence < names.length) return sequence;
  return -1;
}

export function createTourEngine(
  host: HTMLDivElement,
  modelUrl: string,
  onStatus: (message: string | null) => void,
  onError: (error: unknown) => void,
  onProgress?: (progress: ModelProgress) => void,
) {
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    // Máy có hai GPU (laptop) sẽ dùng GPU rời thay vì GPU tích hợp — chênh nhau
    // vài lần khung hình với model photogrammetry cỡ này.
    powerPreference: "high-performance",
  });
  /** Trần tỉ lệ điểm ảnh của máy đang chạy (đọc lúc khởi tạo, không đọc ở SSR). */
  const maxPixelRatio = Math.min(window.devicePixelRatio || 1, MAX_PIXEL_RATIO_CAP);
  renderer.setPixelRatio(maxPixelRatio);
  renderer.domElement.setAttribute(
    "aria-label",
    "Model 3D — kéo ngang để xoay",
  );
  host.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
  const environment = createEnvironment(scene, renderer);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.maxPolarAngle = Math.PI / 2;
  // Scene view chỉ "kéo để nhìn quanh": không zoom, không pan. Chế độ 3D
  // (`enterExplore`) tự bật lại zoom — xem `explore-controller`.
  controls.enableZoom = false;
  controls.enablePan = false;

  const cameraController = createCameraController(camera, controls);
  const boundary = createExploreBoundary(scene);
  const explore = createExploreController(cameraController, controls, {
    camera,
    canvas: renderer.domElement,
    boundary,
  });
  const loader = createModelLoader(renderer);
  const highlights = createInteractiveHighlights(
    scene,
    renderer.domElement,
    (target) => cameraController.setDollyTarget(target),
  );
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
  /** Gốc model đã nạp — cần để tìm node đích và bắn tia khi đọc camera từ GLB. */
  let glbRoot: THREE.Object3D | null = null;
  let disposed = false;

  /**
   * Quỹ đạo camera của cảnh hiện tại (`scene.camera_path_url`).
   *
   * Đây là "nguồn ghi" thứ tư của camera, cùng nhóm với `timeline`: nó tiến theo
   * `playbackClock` nên pause/tua audio là camera theo đúng, và nó nhường quyền
   * ngay khi có chuyến bay hoặc người dùng chủ động đổi góc.
   */
  let cameraPath: CameraPath | null = null;
  let cameraPathUrl: string | null = null;
  /** Tăng mỗi lần đổi path: lần nạp về MUỘN của cảnh cũ không được chiếm quyền. */
  let cameraPathToken = 0;
  /** Thời điểm đã sample — cùng một `seconds` thì không tính lại. */
  let cameraPathTime = Number.NaN;
  let cameraPathNeedsSync = false;

  /** Chỉ đồng bộ drawing buffer theo tỉ lệ điểm ảnh hiện tại (không đụng camera). */
  const syncDrawingBuffer = () => {
    const { width, height } = host.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height);
  };

  const resize = () => {
    const { width, height } = host.getBoundingClientRect();
    if (!width || !height) return;
    explore.resize(cameraController.resize(width, height));
    renderer.setSize(width, height);
    invalidate();
  };

  /**
   * Thích ứng độ phân giải render theo sức máy.
   *
   * Vòng lặp chỉ vẽ khi có gì đó đổi, nên chỉ số frame interval của những frame
   * THỰC SỰ vẽ mới phản ánh tải GPU (frame nhàn rỗi thì `delta` vống lên vài trăm
   * ms, đem so sẽ hạ độ phân giải vô cớ). Vì vậy chỉ gọi `trackFrame` trong nhánh
   * có `renderer.render`, và bỏ qua các frame khựng bất thường (tải model, compile
   * shader) để chúng không kéo trung bình xuống.
   */
  let pixelRatio = maxPixelRatio;
  const adapt = { frames: 0, seconds: 0, cooldown: 0 };
  const trackFrame = (delta: number) => {
    if (delta <= 0 || delta > 0.25) return;
    if (adapt.cooldown > 0) {
      adapt.cooldown -= 1;
      return;
    }
    adapt.frames += 1;
    adapt.seconds += delta;
    if (adapt.frames < ADAPT_WINDOW) return;
    const average = adapt.seconds / adapt.frames;
    adapt.frames = 0;
    adapt.seconds = 0;

    let next = pixelRatio;
    if (average > ADAPT_DOWN_SECONDS && pixelRatio > MIN_PIXEL_RATIO) {
      next = Math.max(MIN_PIXEL_RATIO, pixelRatio - PIXEL_RATIO_STEP);
    } else if (average < ADAPT_UP_SECONDS && pixelRatio < maxPixelRatio) {
      next = Math.min(maxPixelRatio, pixelRatio + PIXEL_RATIO_STEP);
    }
    if (Math.abs(next - pixelRatio) < 1e-3) return;
    pixelRatio = next;
    renderer.setPixelRatio(pixelRatio);
    // `setPixelRatio` chỉ ghi nhận tỉ lệ, drawing buffer đổi ở lần `setSize` kế tiếp.
    // Cố tình KHÔNG gọi `resize()`: hàm đó chỉnh lại khoảng cách camera theo tỉ lệ
    // khung hình, mà ở đây khung hình không đổi — chỉ độ phân giải đổi.
    syncDrawingBuffer();
    adapt.cooldown = ADAPT_COOLDOWN;
  };

  resize();
  const observer = new ResizeObserver(resize);
  observer.observe(host);

  async function load() {
    try {
      const gltf = await loader.load(
        modelUrl,
        () => onStatus("Đang giải mã model và texture…"),
        onProgress,
      );
      if (disposed) return;
      scene.add(gltf.scene);
      glbRoot = gltf.scene;
      glbCameras = gltf.cameras;
      cameraController.fit(gltf.scene);
      // `fit()` vừa ghi đè camera. Nếu quỹ đạo path đã áp pose trước đó (path nạp
      // xong trước model) thì `cameraPathTime` vẫn bằng `playbackClock` và vòng
      // lặp sẽ bỏ qua — camera kẹt ở góc `fit()` cho tới khi audio đổi thời điểm.
      // Hạ mốc thời gian để frame sau áp lại pose của path.
      cameraPathTime = Number.NaN;
    cameraPathNeedsSync = false;
      invalidate();
      onStatus(null);
      // Biên dịch shader của model song song (KHR_parallel_shader_compile) thay vì
      // để frame đầu tiên vừa vẽ vừa compile — cú khựng đó rơi đúng lúc người dùng
      // vừa vào cảnh và dễ bị hiểu là "cảnh này lag".
      void renderer.compileAsync(scene, camera).catch(() => undefined);
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
    const pathMoved = updateCameraPath(playbackClock);
    const cameraDriven = cameraFlying || dollyMoved || timelineMoved || pathMoved;

 
    const walking = explore.isWalking();
    const walkMoved = walking ? explore.updateWalk(delta) : false;
    const cameraChanged = cameraDriven || walking ? false : controls.update();
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
     
      const writer = walking ? "walk" : pathMoved ? "path" : timelineMoved ? "timeline" : dollyMoved ? "dolly" : cameraFlying ? "flight" : "controls";
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

    // Lerp tỉ lệ badge chạy mỗi frame (rẻ) để biết còn animation hay không:
    // badge đang thu nhỏ/phình ra phải kéo theo việc vẽ tiếp, nếu không nó đứng
    // hình sau frame đầu vì vòng lặp này chỉ vẽ khi có gì đó thay đổi.
    const badgesAnimating = highlights.update(camera, delta);

    // `walkMoved` phải có mặt ở đây: khi đi bộ ta đã BỎ `controls.update()` nên
    // `cameraChanged` luôn false, và bước đi không tự sinh frame nào khác — thiếu
    // nó thì người dùng bấm W mà hình đứng im.
    if (cameraDriven || cameraChanged || walkMoved || highlightsChanged || needsRender || badgesAnimating) {
      renderer.render(scene, camera);
      needsRender = false;
      trackFrame(delta);
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

  /** Tên node rỗng được coi là "điểm ngắm" của mọi camera trong GLB. */
  const CAMERA_TARGET_NAMES = ["cam_target", "camera_target", "cameratarget", "target"];

  /** Camera nhúng trong GLB theo tên (không phân biệt hoa thường). */
  const findGLBCamera = (name: string) => {
    const wanted = name.trim().toLowerCase();
    const hit =
      glbCameras.find((item) => item.name === name) ??
      glbCameras.find((item) => item.name.trim().toLowerCase() === wanted);
    // Chỉ camera phối cảnh mới có `fov`; camera trực giao trong GLB bị bỏ qua.
    return hit instanceof THREE.PerspectiveCamera ? hit : null;
  };

  /**
   * Điểm ngắm cho camera đọc từ GLB — thứ OrbitControls quay quanh.
   *
   * Camera trong glTF chỉ có vị trí và hướng; nếu lấy `position + hướng` làm target
   * thì camera quay quanh một điểm cách nó đúng 1 m, với model cỡ vài trăm mét thì
   * mỗi lần kéo chuột là model văng khỏi màn hình. Ưu tiên:
   *   1. node rỗng tên `<tên camera>_target` / `CAM_Target` — tác giả đặt đúng tâm
   *      muốn quay quanh, chính xác nhất;
   *   2. tia bắn từ camera vào model, lấy điểm trúng ĐẦU TIÊN — với model scan thì
   *      đó đúng là thứ camera đang nhìn;
   *   3. `null` ⇒ controller lùi về điểm cách 1 m theo hướng nhìn.
   */
  const resolveCameraTarget = (source: THREE.PerspectiveCamera, name: string) => {
    const wanted = new Set(
      [`${name}_target`, `${name}.target`, ...CAMERA_TARGET_NAMES].map((item) =>
        item.trim().toLowerCase(),
      ),
    );
    const hits: THREE.Object3D[] = [];
    glbRoot?.traverse((object) => {
      if (hits.length > 0 || object === glbRoot) return;
      if (wanted.has(object.name.trim().toLowerCase())) hits.push(object);
    });
    const first = hits[0];
    if (first) {
      const point = first.getWorldPosition(new THREE.Vector3());
      camLog("glb-cam", `target theo node ${first.name} → ${fmtVec(point)}`);
      return point;
    }

    if (!glbRoot) return null;
    const origin = source.getWorldPosition(new THREE.Vector3());
    const direction = source.getWorldDirection(new THREE.Vector3());
    // Raycaster riêng: dùng chung `raycaster` của hover sẽ ghi đè trạng thái con trỏ.
    const probe = new THREE.Raycaster(origin, direction);
    const hit = probe.intersectObject(glbRoot, true)[0];
    if (hit) {
      camLog("glb-cam", `target theo tia chiếu → ${fmtVec(hit.point)} (${hit.distance.toFixed(1)} m)`);
      return hit.point.clone();
    }
    camWarn("glb-cam", "không có node đích và tia chiếu trượt model ⇒ quay quanh điểm cách 1 m");
    return null;
  };

  /** Buông quỹ đạo camera hiện tại. Trả `true` khi thật sự có thứ để buông. */
  const releaseCameraPath = () => {
    cameraPathTime = Number.NaN;
    cameraPathNeedsSync = false;
    cameraPathUrl = null;
    if (!cameraPath) return false;
    cameraPath.dispose();
    cameraPath = null;
    return true;
  };

  /**
   * Áp quỹ đạo camera tại `seconds` — gọi mỗi frame từ vòng lặp render.
   *
   * Nhường ngay khi đang có chuyến bay: chuyến bay chuyển cảnh do
   * `cameraController.update()` ghi, áp thêm pose của path trong cùng frame là
   * hai nguồn cùng viết ⇒ giật. Chuyến bay luôn kết thúc đúng tại `path(0)` nên
   * buông ra là khớp, không nhảy.
   */
  const updateCameraPath = (seconds: number) => {
    if (!cameraPath) return false;
    if (cameraController.isFlying()) return false;
    if (seconds === cameraPathTime) {
      if (cameraPathNeedsSync) {
        cameraPathNeedsSync = false;
        cameraController.finishPathPose();
      }
      return false;
    }
    const pose = cameraPath.sample(seconds);
    if (!pose) return false;
    cameraPathTime = seconds;
    cameraController.applyPathPose(pose.position, pose.target, pose.fov);
    cameraPathNeedsSync = true;
    return true;
  };

  /** Bay tới pose của quỹ đạo tại `seconds` (dùng chung cho vào cảnh / thoát Explore). */
  const flyToPathTime = (seconds: number, duration = 0) => {
    if (!cameraPath) return false;
    const pose = cameraPath.sample(seconds);
    if (!pose) return false;
    cameraController.restore(
      {
        position: pose.position,
        target: pose.target,
        up: new THREE.Vector3(0, 1, 0),
        fov: pose.fov,
      },
      duration,
    );
    invalidate();
    return true;
  };

  /** Đặt camera theo `source` và báo cho vòng lặp render. */
  const applyGLBCamera = (source: THREE.PerspectiveCamera, duration: number) => {
    releaseCameraPath();
    const target = resolveCameraTarget(source, source.name);
    cameraController.useGLBCamera(source, target, duration);
    camLog(
      "glb-cam",
      `dùng camera ${source.name} · pos=${fmtVec(source.getWorldPosition(new THREE.Vector3()))} · fov=${source.fov.toFixed(1)} · target=${fmtVec(target)}`,
    );
    invalidate();
    return true;
  };

  return {
    /** Temporary authoring controls; cleanup restores the normal tour's locks. */
    enableCameraEditing: cameraController.enableEditing,

    enterExplore(mode: ExploreMode, eyeHeight?: number) {
      // Pose trước khi vào Explore là "góc về" khi người dùng bấm Reset.
      cameraController.adoptCurrentPose();
      explore.enter(mode, eyeHeight);
      highlights.show(true);
      invalidate();
    },

    setExploreArea(area: ExploreArea | null) {
      explore.setArea(area);
      invalidate();
    },
    /** Bầu trời + đèn + sương mù của cảnh hiện tại (preset `threeJS_skySet`). */
    setSky(preset: HeritageSkyPreset | null) {
      environment.apply(preset);
      invalidate();
    },
    /**
     * Cần gạt ảo trên mobile. Không gọi `invalidate()`: `updateWalk()` trả về
     * `true` khi camera dịch chuyển và vòng lặp render đã tự vẽ frame đó.
     */
    setWalkStick(x: number, y: number) {
      explore.setWalkStick(x, y);
    },
    releaseWalkStick() {
      explore.releaseWalkStick();
    },
    resetExplore(duration = 0) {
      cameraController.clearDollyTarget();
      explore.reset(duration);
      invalidate();
    },
    exitExplore(duration = 0) {
      cameraController.clearDollyTarget();
      explore.exit(duration);
      highlights.show(false);
      highlights.select(null);
      invalidate();
    },
    showHighlights(visible: boolean) {
      highlights.show(visible);
      if (!visible) cameraController.clearDollyTarget();
      invalidate();
    },
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
      // Pose đặt tay thắng quỹ đạo tự động — nếu không, frame sau path kéo camera về.
      releaseCameraPath();
      const applied = cameraController.applyPreset(preset, zoom);
      invalidate();
      return applied;
    },
    flyCameraPreset(preset: HeritageCamera, zoom = false, duration = 1.6) {
      releaseCameraPath();
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
    /**
     * Nạp quỹ đạo camera của cảnh (`scene.camera_path_url`) — GLB chỉ chứa
     * camera + animation clip, không mesh.
     *
     * Trả `true` khi có clip dùng được. `false` (URL rỗng, tải lỗi, file không có
     * camera/clip) nghĩa là nơi gọi phải lùi về preset A/B như trước.
     *
     * Nạp lại cùng một URL là no-op: đổi cảnh rồi quay lại không tải lại file.
     */
    async setCameraPath(url: string | null): Promise<boolean> {
      if (!url) {
        cameraPathToken += 1;
        if (releaseCameraPath()) invalidate();
        return false;
      }
      if (cameraPath && cameraPathUrl === url) return true;

      const token = ++cameraPathToken;
      try {
        // Dùng chung loader (và cache) với model: file path chỉ vài chục KB nên
        // nằm lại cache cũng không đáng kể, đổi lại là đổi cảnh không tải lại.
        const gltf = await loader.load(url);
        // Cảnh đã đổi (hoặc engine đã đóng) trong lúc chờ ⇒ lần nạp này vô nghĩa.
        if (disposed || token !== cameraPathToken) return false;
        releaseCameraPath();
        const path = createCameraPath(gltf, url, glbRoot);
        if (!path) return false;
        cameraPath = path;
        cameraPathUrl = url;
        cameraPathTime = Number.NaN;
    cameraPathNeedsSync = false;
        camLog(
          "path",
          `nạp ${url} · clip=${path.clipName} · ${path.duration.toFixed(2)}s · camera=${path.cameraName} · target=${path.targetSource()}`,
        );
        invalidate();
        return true;
      } catch (error) {
        if (!disposed && token === cameraPathToken) {
          camWarn("path", `không nạp được quỹ đạo camera ${url}`, error);
        }
        return false;
      }
    },
    /**
     * Bay từ góc đang thấy tới pose của quỹ đạo tại `seconds`.
     *
     * Cùng vai trò với chuyến bay vào preset lúc đổi cảnh: khung đầu của clip
     * chính là góc mở đầu cảnh, nên path và chuyến bay kết thúc ở cùng một pose —
     * buông chuyến bay ra là path tiếp quản, không nhảy.
     */
    applyCameraPathStart(duration = 0) {
      return flyToPathTime(duration <= 0 ? playbackClock : 0, duration);
    },
    /**
     * Quay lại quỹ đạo tại ĐÚNG thời điểm audio đang phát.
     *
     * Dùng khi thoát Explore: tua về khung đầu sẽ lệch với lời thuyết minh đang
     * chạy dở, nên phải bám đồng hồ playback hiện tại.
     */
    resumeCameraPath(duration = 1.2) {
      return flyToPathTime(playbackClock, duration);
    },
    /** Trả quyền camera lại cho preset/người dùng (khi rời cảnh hoặc vào Explore). */
    stopCameraPath() {
      cameraPathToken += 1;
      if (releaseCameraPath()) invalidate();
    },
    hasCameraPath: () => cameraPath !== null,
    /** Thời lượng clip quỹ đạo (giây) — 0 khi cảnh không có path. */
    getCameraPathDuration: () => cameraPath?.duration ?? 0,
    isCameraFlying: cameraController.isFlying,
    /**
     * Đặt camera theo camera nướng sẵn trong GLB, chọn theo TÊN (`camera_node_name`).
     *
     * Dùng khi cảnh KHÔNG có toạ độ tác giả (`cam_start_pos/cam_start_target`) —
     * toạ độ trong DB luôn thắng, vì nó không phụ thuộc vào việc model được xuất
     * lại với tên node khác.
     *
     * Trả `false` khi GLB không có camera tên đó để nơi gọi còn lùi về preset/fit.
     */
    useGLBCamera(name: string, duration = 0) {
      const source = findGLBCamera(name);
      if (!source) {
        camWarn(
          "glb-cam",
          `GLB không có camera phối cảnh tên ${JSON.stringify(name)} (đang có: ${glbCameras.map((c) => c.name).join(", ") || "không có"})`,
        );
        return false;
      }
      return applyGLBCamera(source, duration);
    },
    /**
     * Mỗi cảnh tự lấy camera của mình trong GLB.
     *
     * Khác `useGLBCamera` ở chỗ không cần biết tên: tên được suy theo `sequence`
     * (`Cam_S2`, `Camera_2`, `S2_Cam`…) hoặc, khi GLB có đúng bằng số cảnh, theo
     * đúng thứ tự node. Nhờ vậy chỉ cần export GLB có camera đặt tên đúng là mỗi
     * cảnh có góc riêng, không phải sửa DB.
     */
    useGLBCameraForScene(spec: GLBCameraSceneSpec, duration = 0) {
      const names = glbCameras.map((camera) => camera.name);
      const index = pickGLBCamera(names, spec.sequence, spec.sceneCount);
      const source = index >= 0 ? glbCameras[index] : null;
      if (!(source instanceof THREE.PerspectiveCamera)) {
        camWarn(
          "glb-cam",
          `không chọn được camera cho cảnh ${spec.sequence} (GLB có: ${names.join(", ") || "không camera nào"})`,
        );
        return false;
      }
      return applyGLBCamera(source, duration);
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
      releaseCameraPath();
      observer.disconnect();
      renderer.setAnimationLoop(null);
      renderer.domElement.removeEventListener("pointermove", onPointerMove);
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      detachPointerState();
      highlights.dispose();
      timedHighlights.dispose();
      boundary.dispose();
      environment.dispose();
      controls.dispose();
      loader.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    },
  };
}

export type TourEngine = ReturnType<typeof createTourEngine>;
