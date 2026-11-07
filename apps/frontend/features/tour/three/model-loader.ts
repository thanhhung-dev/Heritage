import * as THREE from "three";
import { GLTFLoader, type GLTF } from "three/addons/loaders/GLTFLoader.js";
import { KTX2Loader } from "three/addons/loaders/KTX2Loader.js";
import { DRACOLoader } from "three/addons/loaders/DRACOLoader.js";

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

/** Tiến độ tải GLB — `ratio` = 0..1, `total` = 0 khi server không trả Content-Length. */
export type ModelProgress = {
  loaded: number;
  total: number;
  ratio: number;
};

/**
 * Đọc body theo luồng để báo tiến độ thật.
 *
 * `response.arrayBuffer()` không cho biết đã nhận được bao nhiêu, nên với model
 * ~100 MB thì thanh loading sẽ đứng im. Đọc bằng `getReader()` cho phép cộng dồn
 * từng chunk và chia cho `Content-Length` của R2.
 */
async function readWithProgress(
  response: Response,
  onProgress?: (progress: ModelProgress) => void,
): Promise<ArrayBuffer> {
  const total = Number(response.headers.get("content-length")) || 0;
  if (!response.body) {
    const buffer = await response.arrayBuffer();
    onProgress?.({ loaded: buffer.byteLength, total: buffer.byteLength, ratio: 1 });
    return buffer;
  }

  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let loaded = 0;
  // Chỉ báo khi % đổi — model 100 MB đọc theo chunk sẽ bắn hàng nghìn lần
  // callback, mỗi lần một lần render React.
  let lastPercent = -1;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    loaded += value.byteLength;
    // Giữ dưới 1 cho tới khi giải mã xong: tải xong byte chưa có nghĩa là model dùng được.
    const ratio = total > 0 ? Math.min(loaded / total, 0.99) : 0;
    const percent = Math.floor(ratio * 100);
    if (percent !== lastPercent) {
      lastPercent = percent;
      onProgress?.({ loaded, total, ratio });
    }
  }

  const buffer = new ArrayBuffer(loaded);
  const view = new Uint8Array(buffer);
  let offset = 0;
  for (const chunk of chunks) {
    view.set(chunk, offset);
    offset += chunk.byteLength;
  }
  // Không bắn ratio = 1 ở đây: tải xong mới là hết bước 1, còn giải mã nữa.
  // Engine báo xong qua `onStatus(null)` → trang splash tự chuyển sang Start.
  return buffer;
}

/** Cache theo URL trong một engine; loader sở hữu tài nguyên của mọi bản clone. */
export function createModelLoader(renderer: THREE.WebGLRenderer) {
  const controller = new AbortController();
  const decoder = new KTX2Loader().setTranscoderPath("/three/basis/").setWorkerLimit(2);
  decoder.detectSupport(renderer);
  const draco = new DRACOLoader().setDecoderPath("/three/draco/").setWorkerLimit(2);
  const loader = new GLTFLoader().setKTX2Loader(decoder).setDRACOLoader(draco);
  const cache = new Map<string, Promise<GLTF>>();
  const models = new Set<THREE.Object3D>();
  let disposed = false;

  async function fetchModel(
    url: string,
    onDecode?: () => void,
    onProgress?: (progress: ModelProgress) => void,
  ) {
    const response = await fetch(url, { signal: controller.signal });
    if (!response.ok) throw new Error(`Không tải được model (HTTP ${response.status}).`);
    const bytes = await readWithProgress(response, onProgress);
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
    load(
      url: string,
      onDecode?: () => void,
      onProgress?: (progress: ModelProgress) => void,
    ) {
      if (disposed) return Promise.reject(new DOMException("Loader đã đóng", "AbortError"));
      let pending = cache.get(url);
      if (!pending) {
        pending = fetchModel(url, onDecode, onProgress).catch((error) => {
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
      draco.dispose();
    },
  };
}

export type ModelLoader = ReturnType<typeof createModelLoader>;
