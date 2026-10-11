import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { KTX2Loader } from "three/addons/loaders/KTX2Loader.js";

function disposeModel(root: THREE.Object3D) {
  const geometries = new Set<THREE.BufferGeometry>();
  const materials = new Set<THREE.Material>();
  const textures = new Set<THREE.Texture>();
  root.traverse((object) => {
    if (!(object instanceof THREE.Mesh)) return;
    geometries.add(object.geometry);
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
      materials.add(material);
      for (const value of Object.values(material)) {
        if (value instanceof THREE.Texture) textures.add(value);
      }
    }
  });
  geometries.forEach((geometry) => geometry.dispose());
  materials.forEach((material) => material.dispose());
  textures.forEach((texture) => {
    texture.dispose();
    if (texture.image instanceof ImageBitmap) texture.image.close();
  });
}

export function createTourEngine(
  host: HTMLDivElement,
  modelUrl: string,
  onStatus: (message: string | null) => void,
  onError: (error: unknown) => void,
) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  renderer.domElement.setAttribute("aria-label", "Model 3D Lăng Tự Đức — kéo để xoay, cuộn để zoom");
  host.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color("#1c1b1a");
  scene.add(new THREE.HemisphereLight(0xffffff, 0x72726b, 2));
  const light = new THREE.DirectionalLight(0xffffff, 2);
  light.position.set(1, 2, 1);
  scene.add(light);

  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.maxPolarAngle = Math.PI / 2;
  let needsRender = true;
  const resize = () => {
    const { width, height } = host.getBoundingClientRect();
    if (!width || !height) return;
    const oldHalfFov = Math.min(
      THREE.MathUtils.degToRad(camera.fov) / 2,
      Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * camera.aspect),
    );
    camera.aspect = width / height;
    const newHalfFov = Math.min(
      THREE.MathUtils.degToRad(camera.fov) / 2,
      Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * camera.aspect),
    );
    // Giữ mức zoom tương đối khi đổi desktop/mobile, không crop model do aspect.
    const ratio = Math.sin(oldHalfFov) / Math.sin(newHalfFov);
    camera.position.sub(controls.target).multiplyScalar(ratio).add(controls.target);
    controls.minDistance *= ratio;
    controls.maxDistance *= ratio;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
    needsRender = true;
  };
  resize();
  const observer = new ResizeObserver(resize);
  observer.observe(host);

  const controller = new AbortController();
  const ktx2 = new KTX2Loader().setTranscoderPath("/three/basis/").setWorkerLimit(2);
  ktx2.detectSupport(renderer);
  const loader = new GLTFLoader().setKTX2Loader(ktx2);
  let disposed = false;
  let model: THREE.Object3D | null = null;

  // Không dùng camera demo hoặc thay đổi transform của model thật.
  async function load() {
    try {
      const response = await fetch(modelUrl, { signal: controller.signal });
      if (!response.ok) throw new Error(`Không tải được model (HTTP ${response.status}).`);
      const bytes = await response.arrayBuffer();
      if (disposed) return;
      onStatus("Đang giải mã model và texture…");
      const gltf = await loader.parseAsync(bytes, modelUrl.slice(0, modelUrl.lastIndexOf("/") + 1));
      if (disposed) {
        disposeModel(gltf.scene);
        return;
      }
      model = gltf.scene;
      scene.add(model);
      model.updateWorldMatrix(true, true);
      const sphere = new THREE.Box3().setFromObject(model).getBoundingSphere(new THREE.Sphere());
      const verticalFov = THREE.MathUtils.degToRad(camera.fov);
      const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect);
      const distance = sphere.radius / Math.sin(Math.min(verticalFov, horizontalFov) / 2) * 1.15;
      controls.target.copy(sphere.center);
      camera.position.copy(sphere.center).addScaledVector(new THREE.Vector3(1, 0.8, 1).normalize(), distance);
      camera.near = Math.max(sphere.radius / 1000, 0.01);
      camera.far = distance + sphere.radius * 100;
      camera.updateProjectionMatrix();
      controls.minDistance = sphere.radius * 0.05;
      controls.maxDistance = distance * 5;
      controls.update();
      needsRender = true;
      onStatus(null);
    } catch (error) {
      if (!disposed) onError(error);
    }
  }
  void load();
  renderer.setAnimationLoop(() => {
    // Model scan tĩnh: chỉ vẽ lại khi camera/canvas/model thay đổi.
    if (controls.update() || needsRender) {
      renderer.render(scene, camera);
      needsRender = false;
    }
  });

  return () => {
    disposed = true;
    controller.abort();
    observer.disconnect();
    renderer.setAnimationLoop(null);
    controls.dispose();
    if (model) disposeModel(model);
    ktx2.dispose();
    renderer.dispose();
    renderer.forceContextLoss();
    renderer.domElement.remove();
  };
}
