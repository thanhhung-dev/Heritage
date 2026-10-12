import * as THREE from "three";
import { GLTFLoader, type GLTF } from "three/addons/loaders/GLTFLoader.js";
import { KTX2Loader } from "three/addons/loaders/KTX2Loader.js";

function disposeModels(roots: Iterable<THREE.Object3D>) {
  const geometries = new Set<THREE.BufferGeometry>();
  const materials = new Set<THREE.Material>();
  const textures = new Set<THREE.Texture>();
  for (const root of roots) root.traverse((object) => {
    if (!(object instanceof THREE.Mesh)) return;
    geometries.add(object.geometry);
    for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
      materials.add(material);
      for (const value of Object.values(material)) {
        if (value instanceof THREE.Texture) textures.add(value);
      }
    }
  });
  geometries.forEach((item) => item.dispose());
  materials.forEach((item) => item.dispose());
  textures.forEach((item) => {
    item.dispose();
    if (item.image instanceof ImageBitmap) item.image.close();
  });
}

/** Cache theo URL trong một engine; loader sở hữu tài nguyên của mọi bản clone. */
export function createModelLoader(renderer: THREE.WebGLRenderer) {
  const controller = new AbortController();
  const decoder = new KTX2Loader().setTranscoderPath("/three/basis/").setWorkerLimit(2);
  decoder.detectSupport(renderer);
  const loader = new GLTFLoader().setKTX2Loader(decoder);
  const cache = new Map<string, Promise<GLTF>>();
  const models = new Set<THREE.Object3D>();
  let disposed = false;

  async function fetchModel(url: string, onDecode?: () => void) {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) throw new Error(`Không tải được model (HTTP ${response.status}).`);
    const bytes = await response.arrayBuffer();
    if (disposed) throw new DOMException("Loader đã đóng", "AbortError");
    onDecode?.();
    const gltf = await loader.parseAsync(bytes, url.slice(0, url.lastIndexOf("/") + 1));
    if (disposed) {
      disposeModels([gltf.scene]);
      throw new DOMException("Loader đã đóng", "AbortError");
    }
    models.add(gltf.scene);
    return gltf;
  }

  return {
    load(url: string, onDecode?: () => void) {
      if (disposed) return Promise.reject(new DOMException("Loader đã đóng", "AbortError"));
      let pending = cache.get(url);
      if (!pending) {
        pending = fetchModel(url, onDecode).catch((error) => {
          cache.delete(url);
          throw error;
        });
        cache.set(url, pending);
      }
      return pending;
    },
    dispose() {
      disposed = true;
      controller.abort();
      disposeModels(models);
      models.clear();
      cache.clear();
      decoder.dispose();
    },
  };
}

export type ModelLoader = ReturnType<typeof createModelLoader>;
