import {
  CompressedTexture,
  FileLoader,
  HalfFloatType,
  LinearFilter,
  LinearMipmapLinearFilter,
  RGBA_ASTC_4x4_Format,
  RGBA_BPTC_Format,
  RGBA_ETC2_EAC_Format,
  RGBA_PVRTC_4BPPV1_Format,
  RGBA_S3TC_DXT1_Format,
  RGBA_S3TC_DXT5_Format,
  RGB_BPTC_UNSIGNED_Format,
  RGB_ETC1_Format,
  RGB_ETC2_Format,
  RGB_PVRTC_4BPPV1_Format,
  UnsignedByteType,
  type CompressedPixelFormat,
  type WebGLRenderer,
} from "three";
import { KTX2Loader } from "three/addons/loaders/KTX2Loader.js";

/**
 * KTX2 đầy đủ phải transcode mọi mip trước khi GLTFLoader trả model — với file
 * nội thất ~100 MB thì cảnh đứng ở màn Loading dù mesh đã sẵn.
 *
 * Loader này trả mip ~128px ngay để model hiện mờ, transcode mip đầy đủ ở nền,
 * rồi hạ `TEXTURE_MIN_LOD` để texture nét dần. Lỗi mip thô thì chờ bản đầy đủ
 * như loader gốc.
 */

const COARSE_MAX = 128;
const SHARPEN_MS = 2200;
const CONFIG_KEYS = [
  "astcSupported",
  "bptcSupported",
  "dxtSupported",
  "etc2Supported",
  "etc1Supported",
  "pvrtcSupported",
] as const;

type WorkerConfig = Partial<Record<(typeof CONFIG_KEYS)[number], boolean>>;
type Mip = { data: Uint8Array; width: number; height: number };
type SharpenJob = { texture: CompressedTexture; from: number; started: number };
type CoarseMessage = {
  type: string;
  id: number;
  error?: string;
  result?: { width: number; height: number; format: number; type: number; data: Uint8Array };
};

const jobs: SharpenJob[] = [];

function readWorkerConfig(loader: KTX2Loader): WorkerConfig | null {
  if (!("workerConfig" in loader)) return null;
  const raw = loader.workerConfig;
  if (!raw || typeof raw !== "object") return null;
  const config: WorkerConfig = {};
  for (const key of CONFIG_KEYS) {
    if (key in raw && typeof raw[key] === "boolean") config[key] = raw[key];
  }
  return config;
}

function mipLodAtMost(mips: { width: number; height: number }[], maxSize: number) {
  for (let i = 0; i < mips.length; i += 1) {
    if (Math.max(mips[i].width, mips[i].height) <= maxSize) return i;
  }
  return Math.max(0, mips.length - 1);
}

const COMPRESSED_FORMATS = new Map<number, CompressedPixelFormat>([
  [RGBA_ASTC_4x4_Format, RGBA_ASTC_4x4_Format],
  [RGBA_BPTC_Format, RGBA_BPTC_Format],
  [RGBA_ETC2_EAC_Format, RGBA_ETC2_EAC_Format],
  [RGBA_PVRTC_4BPPV1_Format, RGBA_PVRTC_4BPPV1_Format],
  [RGBA_S3TC_DXT1_Format, RGBA_S3TC_DXT1_Format],
  [RGBA_S3TC_DXT5_Format, RGBA_S3TC_DXT5_Format],
  [RGB_BPTC_UNSIGNED_Format, RGB_BPTC_UNSIGNED_Format],
  [RGB_ETC1_Format, RGB_ETC1_Format],
  [RGB_ETC2_Format, RGB_ETC2_Format],
  [RGB_PVRTC_4BPPV1_Format, RGB_PVRTC_4BPPV1_Format],
]);

function uploadedTexture(renderer: WebGLRenderer, texture: CompressedTexture): WebGLTexture | null {
  const props = renderer.properties.get(texture);
  if (!props || typeof props !== "object" || !("__webglTexture" in props)) return null;
  const handle = props.__webglTexture;
  if (!handle || typeof handle !== "object") return null;
  return handle as WebGLTexture;
}

export function textureSharpenActive() {
  return jobs.length > 0;
}

export function tickTextureSharpen(renderer: WebGLRenderer): boolean {
  const gl = renderer.getContext() as WebGL2RenderingContext;
  const now = performance.now();
  for (let i = jobs.length - 1; i >= 0; i -= 1) {
    const job = jobs[i];
    const handle = uploadedTexture(renderer, job.texture);
    if (!handle) continue;
    const lod = job.from * (1 - Math.min(1, (now - job.started) / SHARPEN_MS));
    gl.bindTexture(gl.TEXTURE_2D, handle);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_LOD, lod);
    if (lod <= 0) jobs.splice(i, 1);
  }
  return jobs.length > 0;
}

/** Bản đầy đủ vừa gắn vào material đang hiện: lấy mẫu mip thô trước, rồi nét dần. */
export function scheduleTextureSharpen(renderer: WebGLRenderer, texture: CompressedTexture) {
  const mips = texture.mipmaps as { width: number; height: number }[];
  const from = mipLodAtMost(mips, COARSE_MAX);
  renderer.initTexture(texture);
  const gl = renderer.getContext() as WebGL2RenderingContext;
  const handle = uploadedTexture(renderer, texture);
  if (handle) {
    gl.bindTexture(gl.TEXTURE_2D, handle);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_LOD, from);
  }
  jobs.push({ texture, from, started: performance.now() });
}

function createCoarseWorker() {
  const source = `
    importScripts("/three/basis/basis_transcoder.js");
    let BasisModule;
    let ready;
    let config;
    const FORMAT_OPTIONS = [
      { if: "astcSupported", basisFormat: [1], transcoderFormat: [10, 10], engineFormat: [37808, 37808], engineType: [1009], priorityETC1S: Infinity, priorityUASTC: 1 },
      { if: "bptcSupported", basisFormat: [0, 1], transcoderFormat: [7, 7], engineFormat: [36492, 36492], engineType: [1009], priorityETC1S: 3, priorityUASTC: 2 },
      { if: "dxtSupported", basisFormat: [0, 1], transcoderFormat: [2, 3], engineFormat: [33777, 33779], engineType: [1009], priorityETC1S: 4, priorityUASTC: 5 },
      { if: "etc2Supported", basisFormat: [0, 1], transcoderFormat: [0, 1], engineFormat: [37492, 37496], engineType: [1009], priorityETC1S: 1, priorityUASTC: 3 },
      { if: "etc1Supported", basisFormat: [0, 1], transcoderFormat: [0], engineFormat: [36196], engineType: [1009], priorityETC1S: 2, priorityUASTC: 4 },
      { if: "pvrtcSupported", basisFormat: [0, 1], transcoderFormat: [8, 9], engineFormat: [35840, 35842], engineType: [1009], priorityETC1S: 5, priorityUASTC: 6, needsPowerOfTwo: true },
      { if: "bptcSupported", basisFormat: [2], transcoderFormat: [22], engineFormat: [36495], engineType: [1016], priorityHDR: 1 },
      { basisFormat: [0, 1], transcoderFormat: [13, 13], engineFormat: [1023, 1023], engineType: [1009], priorityETC1S: 100, priorityUASTC: 100 },
      { basisFormat: [2], transcoderFormat: [25], engineFormat: [1023], engineType: [1016], priorityHDR: 100 }
    ];
    function isPowerOfTwo(value) {
      return value <= 2 || ((value & (value - 1)) === 0 && value !== 0);
    }
    function getTranscoderFormat(basisFormat, width, height, hasAlpha) {
      const key = basisFormat === 0 ? "priorityETC1S" : basisFormat === 1 ? "priorityUASTC" : "priorityHDR";
      const options = FORMAT_OPTIONS.filter((opt) => opt.basisFormat.includes(basisFormat)).sort((a, b) => a[key] - b[key]);
      for (const opt of options) {
        if (opt.if && !config[opt.if]) continue;
        if (hasAlpha && opt.transcoderFormat.length < 2) continue;
        if (opt.needsPowerOfTwo && !(isPowerOfTwo(width) && isPowerOfTwo(height))) continue;
        const index = hasAlpha ? 1 : 0;
        return { transcoderFormat: opt.transcoderFormat[index], engineFormat: opt.engineFormat[index], engineType: opt.engineType[0] };
      }
      throw new Error("no transcode target");
    }
    function coarse(buffer) {
      const file = new BasisModule.KTX2File(new Uint8Array(buffer));
      const fail = (message) => { file.close(); file.delete(); throw new Error(message); };
      if (!file.isValid()) fail("invalid ktx2");
      if (file.getFaces() !== 1 || (file.getLayers() || 1) !== 1) fail("not a 2D texture");
      const basisFormat = file.isUASTC() ? 1 : file.isETC1S() ? 0 : file.isHDR() ? 2 : -1;
      if (basisFormat < 0) fail("unknown basis");
      const levels = file.getLevels();
      const hasAlpha = file.getHasAlpha();
      const target = getTranscoderFormat(basisFormat, file.getWidth(), file.getHeight(), hasAlpha);
      if (!file.startTranscoding()) fail("startTranscoding");
      let mip = levels - 1;
      for (let i = levels - 1; i >= 0; i -= 1) {
        const info = file.getImageLevelInfo(i, 0, 0);
        mip = i;
        if (Math.max(info.origWidth, info.origHeight) >= ${COARSE_MAX}) break;
      }
      const info = file.getImageLevelInfo(mip, 0, 0);
      const dst = new Uint8Array(file.getImageTranscodedSizeInBytes(mip, 0, 0, target.transcoderFormat));
      if (!file.transcodeImage(dst, mip, 0, 0, target.transcoderFormat, 0, -1, -1)) fail("transcodeImage");
      file.close();
      file.delete();
      return { width: info.origWidth || info.width, height: info.origHeight || info.height, format: target.engineFormat, type: target.engineType, data: dst };
    }
    self.onmessage = (event) => {
      const message = event.data;
      if (message.type === "init") {
        config = message.config;
        ready = new Promise((resolve) => {
          BasisModule = { wasmBinary: message.wasm, onRuntimeInitialized: resolve };
          BASIS(BasisModule);
        }).then(() => BasisModule.initializeBasis());
        return;
      }
      ready.then(() => {
        try {
          const result = coarse(message.buffer);
          self.postMessage({ type: "coarse", id: message.id, result }, [result.data.buffer]);
        } catch (error) {
          self.postMessage({ type: "error", id: message.id, error: String(error && error.message || error) });
        }
      });
    };
  `;
  return new Worker(URL.createObjectURL(new Blob([source], { type: "text/javascript" })));
}

export class ProgressiveKTX2Loader extends KTX2Loader {
  private renderer: WebGLRenderer | null = null;
  private coarseWorker: Worker | null = null;
  private coarseReady: Promise<Worker> | null = null;
  private nextId = 0;

  override detectSupport(renderer: WebGLRenderer) {
    this.renderer = renderer;
    return super.detectSupport(renderer);
  }

  override dispose() {
    this.coarseWorker?.terminate();
    this.coarseWorker = null;
    this.coarseReady = null;
    super.dispose();
  }

  override load(
    url: string,
    onLoad: (texture: CompressedTexture) => void,
    onProgress?: (event: ProgressEvent) => void,
    onError?: (error: unknown) => void,
  ) {
    const fileLoader = new FileLoader(this.manager);
    fileLoader.setPath(this.path);
    fileLoader.setCrossOrigin(this.crossOrigin);
    fileLoader.setWithCredentials(this.withCredentials);
    fileLoader.setRequestHeader(this.requestHeader);
    fileLoader.setResponseType("arraybuffer");
    fileLoader.load(url, (data) => {
      if (!(data instanceof ArrayBuffer)) {
        onError?.(new Error("KTX2 không phải ArrayBuffer"));
        return;
      }
      const fullBuffer = data.slice(0);
      const coarseBuffer = data.slice(0);
      let settled = false;
      const { promise: full, resolve: resolveFull, reject: rejectFull } = Promise.withResolvers<CompressedTexture>();
      this.parse(fullBuffer, resolveFull, rejectFull);
      this.transcodeCoarse(coarseBuffer).then((preview) => {
        if (settled) return;
        settled = true;
        onLoad(preview);
        void full.then((texture) => {
          const renderer = this.renderer;
          if (!renderer) return;
          const mips = texture.mipmaps as Mip[];
          preview.mipmaps = mips;
          preview.image = { width: texture.image.width, height: texture.image.height };
          preview.format = texture.format;
          preview.type = texture.type;
          preview.minFilter = LinearMipmapLinearFilter;
          preview.magFilter = LinearFilter;
          preview.generateMipmaps = false;
          preview.needsUpdate = true;
          const from = mipLodAtMost(mips, COARSE_MAX);
          renderer.initTexture(preview);
          const gl = renderer.getContext() as WebGL2RenderingContext;
          const handle = uploadedTexture(renderer, preview);
          if (handle) {
            gl.bindTexture(gl.TEXTURE_2D, handle);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_LOD, from);
          }
          jobs.push({ texture: preview, from, started: performance.now() });
        }).catch(() => undefined);
      }).catch(() => {
        full.then((texture) => {
          if (settled) return;
          settled = true;
          onLoad(texture);
        }).catch((error: unknown) => {
          if (!settled) onError?.(error);
        });
      });
    }, onProgress, (error) => onError?.(error));
  }

  private transcodeCoarse(buffer: ArrayBuffer) {
    return this.ensureWorker().then((worker) => {
      const { promise, resolve, reject } = Promise.withResolvers<CompressedTexture>();
      const id = this.nextId + 1;
      this.nextId = id;
      const onMessage = (event: MessageEvent<CoarseMessage>) => {
        if (event.data.id !== id) return;
        worker.removeEventListener("message", onMessage);
        const result = event.data.result;
        if (event.data.type === "error" || !result) {
          reject(new Error(event.data.error || "Không transcode được mip thô"));
          return;
        }
        const format = COMPRESSED_FORMATS.get(result.format);
        const type = result.type === HalfFloatType ? HalfFloatType : result.type === UnsignedByteType ? UnsignedByteType : null;
        if (!format || type == null) {
          reject(new Error("Định dạng mip thô không dùng được"));
          return;
        }
        const texture = new CompressedTexture(
          [{ data: result.data, width: result.width, height: result.height }],
          result.width,
          result.height,
          format,
          type,
        );
        texture.minFilter = LinearFilter;
        texture.magFilter = LinearFilter;
        texture.generateMipmaps = false;
        texture.needsUpdate = true;
        resolve(texture);
      };
      worker.addEventListener("message", onMessage);
      worker.postMessage({ type: "coarse", id, buffer }, [buffer]);
      return promise;
    });
  }

  private ensureWorker() {
    if (this.coarseReady) return this.coarseReady;
    const config = readWorkerConfig(this);
    if (!config) return Promise.reject(new Error("KTX2 chưa detectSupport"));
    const worker = createCoarseWorker();
    this.coarseWorker = worker;
    this.coarseReady = fetch("/three/basis/basis_transcoder.wasm")
      .then((response) => {
        if (!response.ok) throw new Error(`Basis WASM HTTP ${response.status}`);
        return response.arrayBuffer();
      })
      .then((wasm) => {
        worker.postMessage({ type: "init", wasm, config }, [wasm]);
        return worker;
      });
    return this.coarseReady;
  }
}
