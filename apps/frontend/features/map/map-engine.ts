import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  createInverseProjection,
  createProjection,
  districtAt,
  filterMainlandDistricts,
  regionAt,
  splitMapPanels,
  type BoundaryCollection,
  type Coordinate,
  type DistrictCollection,
  type DistrictFeature,
} from "./geography";
import {
  createClassicRegion,
  createDistrictHighlight,
  createDistrictLines,
  createHudRing,
  disposeScene,
  MAP_THEME_PRIMARY,
} from "./classic-scene";

export type MarkerAnchor = { coordinate: Coordinate; element: HTMLButtonElement };
export type MapEngine = {
  zoom: (factor: number) => void;
  resetView: () => void;
  focus: (coordinate: Coordinate) => void;
  setMarkers: (markers: MarkerAnchor[]) => void;
  setDistricts: (districts: DistrictCollection | null) => void;
  dispose: () => void;
};

export function createMapEngine(
  host: HTMLDivElement,
  data: BoundaryCollection,
  callbacks: {
    onReady: () => void;
    onError: (message: string) => void;
    onBackgroundClick: () => void;
    onDistrictHover?: (district: DistrictFeature | null, point: { x: number; y: number } | null) => void;
  },
): MapEngine {

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  renderer.setClearColor(0x000000, 0);
  renderer.domElement.setAttribute("role", "img");
  renderer.domElement.setAttribute("aria-label", "Bản đồ 3D Huế và Đà Nẵng. Danh sách di sản có sẵn bên cạnh.");
  renderer.domElement.style.cursor = "grab";
  host.prepend(renderer.domElement);
  // Only the mainland presentation is displayed. The source GeoJSON, including
  // offshore polygons, is retained unchanged; there is no inset or moved island.
  const { mainland } = splitMapPanels(data);
  const project = createProjection(mainland);
  const unproject = createInverseProjection(mainland);
  const scene = new THREE.Scene();
  scene.add(new THREE.AmbientLight(MAP_THEME_PRIMARY, 1.45));
  const light = new THREE.DirectionalLight("#fff0dd", 2.4);
  light.position.set(120, -240, 420);
  scene.add(light);
  const camera = new THREE.PerspectiveCamera(31, 1, 1, 10000);
  camera.up.set(0, 0, 1);
  const root = new THREE.Group();
  root.rotation.z = -0.09;
  scene.add(root);
  const surfaces: ReturnType<typeof createClassicRegion>[] = [];
  const hud = createHudRing();
  root.add(hud.plate);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = false;
  controls.dampingFactor = 0.08;
  controls.enableRotate = false;
  controls.enablePan = true;
  controls.screenSpacePanning = false;
  controls.mouseButtons = {
    LEFT: THREE.MOUSE.PAN,
    MIDDLE: THREE.MOUSE.DOLLY,
    RIGHT: THREE.MOUSE.PAN,
  };
  controls.touches = {
    ONE: THREE.TOUCH.PAN,
    TWO: THREE.TOUCH.DOLLY_PAN,
  };
  controls.minPolarAngle = 0.25;
  controls.maxPolarAngle = 1.15;
  controls.minDistance = 120;
  controls.maxDistance = 3000;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let disposed = false, ready = false, frame = 0;
  let fittedDistance = 0;
  const panCenter = new THREE.Vector3();
  const panHalfExtent = new THREE.Vector2(400, 300);
  const initialCameraPosition = new THREE.Vector3();
  const initialTarget = new THREE.Vector3();
  let markers: MarkerAnchor[] = [];
  let width = 1, height = 1;
  let pointerDown: { x: number; y: number } | null = null;
  let lastWheel = 0;
  let flight: { from: THREE.Vector3; to: THREE.Vector3; fromTarget: THREE.Vector3; target: THREE.Vector3; start: number | null } | null = null;
  const cancelFlight = () => { flight = null; };
  const onControlsStart = () => {
    cancelFlight();
    renderer.domElement.style.cursor = "grabbing";
  };
  const onControlsEnd = () => {
    renderer.domElement.style.cursor = "grab";
  };
  const clampPan = () => {
    if (!ready || !fittedDistance) return;
    const clampedX = THREE.MathUtils.clamp(controls.target.x, panCenter.x - panHalfExtent.x, panCenter.x + panHalfExtent.x);
    const clampedY = THREE.MathUtils.clamp(controls.target.y, panCenter.y - panHalfExtent.y, panCenter.y + panHalfExtent.y);
    const dx = clampedX - controls.target.x;
    const dy = clampedY - controls.target.y;
    if (dx !== 0 || dy !== 0) {
      controls.target.x = clampedX;
      controls.target.y = clampedY;
      camera.position.x += dx;
      camera.position.y += dy;
    }
  };
  controls.addEventListener("start", onControlsStart);
  controls.addEventListener("end", onControlsEnd);
  controls.addEventListener("change", clampPan);
  const onPointerDown = (event: PointerEvent) => {
    pointerDown = { x: event.clientX, y: event.clientY };
  };
  const onPointerUp = (event: PointerEvent) => {
    if (!pointerDown) return;
    const distance = Math.hypot(event.clientX - pointerDown.x, event.clientY - pointerDown.y);
    pointerDown = null;
    if (distance <= 6 && performance.now() - lastWheel > 250) callbacks.onBackgroundClick();
  };
  const onPointerCancel = () => { pointerDown = null; };
  let mainlandDistricts: DistrictCollection | null = null;
  let districtLines: THREE.LineSegments | null = null;
  let districtHighlight: THREE.LineSegments | null = null;
  let hoveredDistrictId: string | null = null;
  const raycaster = new THREE.Raycaster();
  const pointerNdc = new THREE.Vector2();
  const surfacePlane = new THREE.Plane();
  const planeNormal = new THREE.Vector3();
  const planePoint = new THREE.Vector3();
  const hitPoint = new THREE.Vector3();

  const clearDistrictLine = (line: THREE.LineSegments | null) => {
    if (!line) return null;
    root.remove(line);
    line.geometry.dispose();
    (line.material as THREE.Material).dispose();
    return null;
  };

  const onPointerMove = (event: PointerEvent) => {
    if (!ready || !mainlandDistricts) return;
    const rect = renderer.domElement.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;
    pointerNdc.set(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1,
    );
    raycaster.setFromCamera(pointerNdc, camera);
    root.updateMatrixWorld(true);
    planeNormal.set(0, 0, 1).transformDirection(root.matrixWorld);
    planePoint.set(0, 0, 44).applyMatrix4(root.matrixWorld);
    surfacePlane.setFromNormalAndCoplanarPoint(planeNormal, planePoint);

    let hit: DistrictFeature | null = null;
    if (raycaster.ray.intersectPlane(surfacePlane, hitPoint)) {
      root.worldToLocal(hitPoint);
      hit = districtAt(mainlandDistricts, unproject([hitPoint.x, hitPoint.y]));
    }
    const nextId = hit?.properties.id ?? null;
    if (nextId !== hoveredDistrictId) {
      hoveredDistrictId = nextId;
      districtHighlight = clearDistrictLine(districtHighlight);
      if (hit) {
        districtHighlight = createDistrictHighlight(hit, project);
        root.add(districtHighlight);
      }
    }
    callbacks.onDistrictHover?.(
      hit,
      hit ? { x: event.clientX - rect.left, y: event.clientY - rect.top } : null,
    );
  };

  const onPointerLeave = () => {
    if (!hoveredDistrictId) return;
    hoveredDistrictId = null;
    districtHighlight = clearDistrictLine(districtHighlight);
    callbacks.onDistrictHover?.(null, null);
  };

  const onWheel = () => { lastWheel = performance.now(); };
  renderer.domElement.addEventListener("pointerdown", onPointerDown);
  renderer.domElement.addEventListener("pointerup", onPointerUp);
  renderer.domElement.addEventListener("pointercancel", onPointerCancel);
  renderer.domElement.addEventListener("pointermove", onPointerMove);
  renderer.domElement.addEventListener("pointerleave", onPointerLeave);
  renderer.domElement.addEventListener("wheel", onWheel, { passive: true });

  function resetView() {
    if (!ready) return;

    controls.enableDamping = false;
    controls.update();
    controls.enableDamping = true;

    if (reducedMotion.matches) {
      flight = null;

      camera.position.copy(initialCameraPosition);
      controls.target.copy(initialTarget);

      controls.update();
      return;
    }

    flight = {
      from: camera.position.clone(),
      to: initialCameraPosition.clone(),
      fromTarget: controls.target.clone(),
      target: initialTarget.clone(),
      start: null,
    };
  }

  function focus(coordinate: Coordinate) {
    if (!ready || !regionAt(mainland, coordinate)) return;
    controls.enableDamping = false;
    controls.update();
    controls.enableDamping = true;
    const [x, y] = project(coordinate);
    root.updateMatrixWorld(true);
    const target = root.localToWorld(new THREE.Vector3(x, y, 52));
    const offset = camera.position.clone().sub(controls.target);
    offset.setLength(Math.min(offset.length(), 400));
    if (width > 760) {
      const focusShiftX = (Math.min(width * 0.12, 170) / height) *
        (2 * offset.length() * Math.tan(THREE.MathUtils.degToRad(31 / 2)));
      target.x -= focusShiftX;
    }
    const position = target.clone().add(offset);
    if (reducedMotion.matches) {
      flight = null;
      controls.target.copy(target);
      camera.position.copy(position);
      controls.update();
    } else {
      flight = { from: camera.position.clone(), to: position, fromTarget: controls.target.clone(), target, start: null };
    }
  }

  function resize() {
    const nextWidth = Math.max(1, host.clientWidth), nextHeight = Math.max(1, host.clientHeight);
    if (nextWidth === width && nextHeight === height && fittedDistance) return;
    width = nextWidth; height = nextHeight;
    cancelFlight();
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    if (!ready) return;
    root.updateMatrixWorld(true);
    const bounds = new THREE.Box3();
    surfaces.forEach((surface) => bounds.expandByObject(surface.group));
    const center = bounds.getCenter(new THREE.Vector3());
    const size = bounds.getSize(new THREE.Vector3());
    const isDesktop = width > 760;
    const targetW = isDesktop ? Math.max(320, Math.min(width - 380, 860)) : width;
    const targetH = isDesktop ? Math.max(360, Math.min(height - 172, 680)) : height;
    const tanHalfFov = Math.tan(THREE.MathUtils.degToRad(31 / 2));
    const visibleHeightNeeded = Math.max(size.y * (height / targetH), size.x * (height / targetW));
    const distance = visibleHeightNeeded / (2 * tanHalfFov) * 1.32;
    const shiftX = isDesktop ? (Math.min(width * 0.15, 210) / height) * (2 * distance * tanHalfFov) : 0;
    const framedTarget = new THREE.Vector3(center.x - shiftX, center.y, center.z);
    panCenter.copy(framedTarget);
    panHalfExtent.set(size.x * 0.75, size.y * 0.75);
    if (fittedDistance) {
      const offset = camera.position.clone().sub(controls.target).multiplyScalar(distance / fittedDistance);
      offset.setLength(THREE.MathUtils.clamp(offset.length(), controls.minDistance, controls.maxDistance));
      camera.position.copy(controls.target).add(offset);
    } else {
      controls.target.copy(framedTarget);
      camera.position.copy(framedTarget).add(new THREE.Vector3(0, -0.75, 0.95).normalize().multiplyScalar(distance));
    }
    fittedDistance = distance;
    controls.update();
    initialTarget.copy(framedTarget);

    initialCameraPosition
      .copy(framedTarget)
      .add(
        new THREE.Vector3(0, -0.75, 0.95).normalize().multiplyScalar(distance),
      );
    controls.target0.copy(framedTarget);
    controls.position0.copy(framedTarget).add(new THREE.Vector3(0, -0.75, 0.95).normalize().multiplyScalar(distance));
  }
  const observer = new ResizeObserver(resize);
  observer.observe(host);

  function onContextLost(event: Event) {
    event.preventDefault();
    if (disposed) return;
    ready = false;
    cancelAnimationFrame(frame); frame = 0;
    callbacks.onError("Mất kết nối WebGL. Hãy tải lại bản đồ.");
  }
  renderer.domElement.addEventListener("webglcontextlost", onContextLost);

  function animate(now: number) {
    frame = 0;
    if (disposed || !ready || document.hidden) return;
    if (flight) {
      // Start on the first rendered frame, not during a possibly expensive card update.
      flight.start ??= now;
      const progress = Math.min(1, (now - flight.start) / 700);
      const ease = 1 - Math.pow(1 - progress, 3);
      camera.position.lerpVectors(flight.from, flight.to, ease);
      controls.target.lerpVectors(flight.fromTarget, flight.target, ease);
      if (progress === 1) flight = null;
    }
    controls.update();
    surfaces.forEach((surface) => surface.update(now / 1000, reducedMotion.matches));
    hud.update(now / 1000, reducedMotion.matches);
    renderer.render(scene, camera);
    for (const marker of markers) {
      const [x, y] = project(marker.coordinate);
      const point = root.localToWorld(new THREE.Vector3(x, y, 52)).project(camera);
      marker.element.style.visibility = Math.abs(point.x) > 1 || Math.abs(point.y) > 1 ||
        point.z < -1 || point.z > 1 ? "hidden" : "visible";
      marker.element.style.transform = `translate(${(point.x * 0.5 + 0.5) * width}px, ${(-point.y * 0.5 + 0.5) * height}px) translate(-50%, -50%)`;
    }
    frame = requestAnimationFrame(animate);
  }
  function onVisibility() {
    if (document.hidden) { cancelAnimationFrame(frame); frame = 0; }
    else if (ready && !frame) frame = requestAnimationFrame(animate);
  }
  document.addEventListener("visibilitychange", onVisibility);
  resize();
  for (const feature of mainland.features) {
    const surface = createClassicRegion(feature, project);
    root.add(surface.group);
    surfaces.push(surface);
  }
  ready = true;
  resize();
  // Publish readiness after React has received the engine handle, including
  // StrictMode's setup/cleanup cycle and a selection made before map mount.
  queueMicrotask(() => {
    if (disposed) return;
    renderer.domElement.dataset.mapReady = "true";
    callbacks.onReady();
    if (!document.hidden) frame = requestAnimationFrame(animate);
  });

  return {
    focus,
    resetView,
    zoom(factor) {
      cancelFlight();
      if (!ready) return;
      const offset = camera.position.clone().sub(controls.target);
      offset.setLength(THREE.MathUtils.clamp(offset.length() * factor, controls.minDistance, controls.maxDistance));
      camera.position.copy(controls.target).add(offset);
      controls.update();
    },
    setMarkers(value) {
      markers = value.filter((marker) => {
        marker.element.style.visibility = "hidden";
        return regionAt(mainland, marker.coordinate) !== null;
      });
    },
    setDistricts(value) {
      districtLines = clearDistrictLine(districtLines);
      districtHighlight = clearDistrictLine(districtHighlight);
      hoveredDistrictId = null;
      callbacks.onDistrictHover?.(null, null);
      mainlandDistricts = value ? filterMainlandDistricts(value) : null;
      if (mainlandDistricts?.features.length) {
        districtLines = createDistrictLines(mainlandDistricts, project);
        root.add(districtLines);
      }
    },
    dispose() {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      renderer.domElement.removeEventListener("pointercancel", onPointerCancel);
      renderer.domElement.removeEventListener("pointermove", onPointerMove);
      renderer.domElement.removeEventListener("pointerleave", onPointerLeave);
      renderer.domElement.removeEventListener("wheel", onWheel);
      controls.removeEventListener("start", onControlsStart);
      controls.removeEventListener("end", onControlsEnd);
      controls.removeEventListener("change", clampPan);
      controls.dispose();
      disposeScene(scene);
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    },
  };
}
