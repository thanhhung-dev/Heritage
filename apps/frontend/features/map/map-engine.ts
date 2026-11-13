import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { createProjection, regionAt, splitMapPanels, type BoundaryCollection, type Coordinate } from "./geography";
import { createClassicRegion, createHudRing, disposeScene, MAP_THEME_PRIMARY } from "./classic-scene";

export type MarkerAnchor = { coordinate: Coordinate; element: HTMLButtonElement };
export type MapEngine = {
  zoom: (factor: number) => void;
  resetView: () => void;
  focus: (coordinate: Coordinate) => void;
  setMarkers: (markers: MarkerAnchor[]) => void;
  dispose: () => void;
};

export function createMapEngine(
  host: HTMLDivElement,
  data: BoundaryCollection,
  callbacks: {
    onReady: () => void;
    onError: (message: string) => void;
    onBackgroundClick: () => void;
  },
): MapEngine {

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  renderer.setClearColor(0x000000, 0);
  renderer.domElement.setAttribute("role", "img");
  renderer.domElement.setAttribute("aria-label", "Bản đồ 3D Huế và Đà Nẵng. Danh sách di sản có sẵn bên cạnh.");
  renderer.domElement.style.cursor = "default";
  host.prepend(renderer.domElement);
  // Only the mainland presentation is displayed. The source GeoJSON, including
  // offshore polygons, is retained unchanged; there is no inset or moved island.
  const { mainland } = splitMapPanels(data);
  const project = createProjection(mainland);
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
  controls.enablePan = false;
  controls.minPolarAngle = 0.25;
  controls.maxPolarAngle = 1.15;
  controls.minDistance = 120;
  controls.maxDistance = 3000;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let disposed = false, ready = false, frame = 0;
  let fittedDistance = 0;
  const initialCameraPosition = new THREE.Vector3();
  const initialTarget = new THREE.Vector3();
  let markers: MarkerAnchor[] = [];
  let width = 1, height = 1;
  let pointerDown: { x: number; y: number } | null = null;
  let lastWheel = 0;
  let flight: { from: THREE.Vector3; to: THREE.Vector3; fromTarget: THREE.Vector3; target: THREE.Vector3; start: number | null } | null = null;
  const cancelFlight = () => { flight = null; };
  controls.addEventListener("start", cancelFlight);
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
  const onWheel = () => { lastWheel = performance.now(); };
  renderer.domElement.addEventListener("pointerdown", onPointerDown);
  renderer.domElement.addEventListener("pointerup", onPointerUp);
  renderer.domElement.addEventListener("pointercancel", onPointerCancel);
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
    const distance = Math.max(size.y, size.x / camera.aspect) /
      (2 * Math.tan(THREE.MathUtils.degToRad(31 / 2))) * 1.32;
    if (fittedDistance) {
      const offset = camera.position.clone().sub(controls.target).multiplyScalar(distance / fittedDistance);
      offset.setLength(THREE.MathUtils.clamp(offset.length(), controls.minDistance, controls.maxDistance));
      camera.position.copy(controls.target).add(offset);
    } else {
      controls.target.copy(center);
      camera.position.copy(center).add(new THREE.Vector3(0, -0.75, 0.95).normalize().multiplyScalar(distance));
    }
    fittedDistance = distance;
    controls.update();
    initialTarget.copy(center);

    initialCameraPosition
      .copy(center)
      .add(
        new THREE.Vector3(0, -0.75, 0.95).normalize().multiplyScalar(distance),
      );
    controls.target0.copy(center);
    controls.position0.copy(center).add(new THREE.Vector3(0, -0.75, 0.95).normalize().multiplyScalar(distance));
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
    if (!reducedMotion.matches) hud.rotor.rotation.z = now * 0.00012;
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
    dispose() {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      renderer.domElement.removeEventListener("pointercancel", onPointerCancel);
      renderer.domElement.removeEventListener("wheel", onWheel);
      controls.removeEventListener("start", cancelFlight);
      controls.dispose();
      disposeScene(scene);
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    },
  };
}
