import * as THREE from "three";
import { Sky } from "three/addons/objects/Sky.js";
import type { HeritageSkyPreset } from "@/types/heritage";

/**
 * Môi trường 3D của tour: bầu trời vật lý (`Sky` của three.js) + sương mù +
 * đèn bán cầu/đèn định hướng, lấy đúng bộ tham số `threeJS_skySet` của bản gốc
 * (xem `features/tour/tapestry.html`, khoá `threeJS_skySet`).
 *
 * TỐI ƯU QUAN TRỌNG — bầu trời KHÔNG nằm trong scene thật.
 * Shader tán xạ khí quyển của `Sky` rất nặng (chuỗi `pow`/`exp` + nhánh mây chạy
 * trên TỪNG pixel kín màn hình). Trước đây khối trời là một mesh trong scene nên
 * mỗi frame đều phải chạy lại toàn bộ shader đó — đây là khoản ngốn GPU lớn nhất
 * của cả cảnh (nhất là cảnh đêm s1, nơi bầu trời phủ kín khung hình mà gần như
 * không có gì che). Nay mỗi lần đổi cảnh ta "nướng" bầu trời MỘT lần thành cubemap
 * HDR (`CubeCamera`) rồi gán `scene.background`; mỗi frame chỉ còn một lần lấy mẫu
 * texture. Ảnh môi trường (PMREM) cũng sinh từ đúng lần nướng đó.
 *
 * Bầu trời chỉ phụ thuộc HƯỚNG nhìn nên nướng thành cubemap là chính xác tuyệt
 * đối, không sai lệch so với mesh sống (mesh cũ bám theo camera, tức parallax = 0).
 */

/**
 * Cạnh hộp trời lúc nướng. `Sky` là `BoxGeometry` cạnh 1 nên hệ số này chính là
 * kích thước hộp; `CubeCamera` đặt ở gốc nên nửa cạnh phải nhỏ hơn `far` của nó.
 */
const SKY_BOX_SCALE = 1000;

/**
 * Độ phân giải một mặt cubemap bầu trời. 1024 đủ mịn cho gradient + mây (bầu trời
 * là nền, không có chi tiết nhỏ). Mobile hạ còn 512: bầu trời ở đó chiếm ít pixel
 * hơn, mà cubemap RGBA16F 1024 tốn ~50 MB VRAM — quá tay với máy yếu.
 */
function skyCubeSize() {
  if (typeof window === "undefined") return 1024;
  return window.matchMedia("(max-width: 768px)").matches ? 512 : 1024;
}

/**
 * Độ phân giải ảnh môi trường PMREM — mặc định của three và cũng là cỡ bản gốc
 * dùng. Phải là bản nướng RIÊNG ở cỡ nhỏ: `PMREMGenerator.fromCubemap` chạy
 * convolution ở đúng cỡ cubemap đầu vào, đưa cubemap 1024 vào sẽ đắt gấp ~16 lần.
 */
const ENV_SIZE = 256;

/**
 * Độ sáng ảnh môi trường sinh từ bầu trời —
 * `threeJS_sets.tjs_settings.sky.environmentIntensity` của bản gốc.
 */
const ENVIRONMENT_INTENSITY = 0.15;

/** Giá trị dự phòng khi preset thiếu trường (hoặc scene không có sky). */
const DEFAULTS = {
  turbidity: 10,
  rayleigh: 2,
  mieCoefficient: 0.005,
  mieDirectionalG: 0.8,
  cloudCoverage: 0,
  cloudDensity: 0,
  elevation: 2,
  azimuth: 180,
  exposure: 1,
  hemiColor: "#ffffff",
  hemiGroundColor: "#444444",
  hemiIntensity: 1,
  dirColor: "#ffffff",
  dirIntensity: 1,
  dirPosition: [1, 2, 1] as const,
};

function readNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function readColor(value: unknown): string | null {
  return typeof value === "string" && value.trim() !== "" ? value : null;
}

function readRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object"
    ? (value as Record<string, unknown>)
    : null;
}

export function createEnvironment(
  scene: THREE.Scene,
  renderer: THREE.WebGLRenderer,
) {
  renderer.toneMapping = THREE.ACESFilmicToneMapping;

  const hemiLight = new THREE.HemisphereLight(
    DEFAULTS.hemiColor,
    DEFAULTS.hemiGroundColor,
    DEFAULTS.hemiIntensity,
  );
  scene.add(hemiLight);

  const dirLight = new THREE.DirectionalLight(
    DEFAULTS.dirColor,
    DEFAULTS.dirIntensity,
  );
  dirLight.position.set(...DEFAULTS.dirPosition);
  scene.add(dirLight);

  /**
   * Scene tạm chỉ chứa khối trời — dùng cho cả lần nướng background lẫn lần render
   * ảnh môi trường. Không add vào `scene` thật (xem chú thích đầu file).
   */
  const skyScene = new THREE.Scene();
  const sky = new Sky();
  sky.scale.setScalar(SKY_BOX_SCALE);
  skyScene.add(sky);

  const skyTarget = new THREE.WebGLCubeRenderTarget(skyCubeSize(), {
    type: THREE.HalfFloatType,
    generateMipmaps: false,
    minFilter: THREE.LinearFilter,
    magFilter: THREE.LinearFilter,
  });
  const skyCamera = new THREE.CubeCamera(1, SKY_BOX_SCALE * 2, skyTarget);

  const pmrem = new THREE.PMREMGenerator(renderer);
  let envTarget: THREE.WebGLRenderTarget | null = null;
  /** Bộ tham số đã nướng — tránh nướng lại khi hai cảnh dùng chung một bầu trời. */
  let bakedSignature: string | null = null;

  const uniforms = sky.material.uniforms;

  /**
   * Nướng bầu trời hiện tại thành cubemap và dùng làm `scene.background`.
   *
   * Nướng ở dạng TUYẾN TÍNH (tắt tone mapping): shader của `Sky` có
   * `#include <tonemapping_fragment>` nên nếu để tone mapping bật, cubemap đã bị
   * ép sáng một lần rồi lúc vẽ background bị ép sáng lần nữa — cả nền lẫn ảnh môi
   * trường đều sai tông. Tắt đi thì background tự áp tone mapping + phơi sáng của
   * cảnh lúc vẽ, giống hệt mesh trời sống trước đây.
   */
  const bakeSky = () => {
    const toneMapping = renderer.toneMapping;
    const exposure = renderer.toneMappingExposure;
    renderer.toneMapping = THREE.NoToneMapping;
    renderer.toneMappingExposure = 1;
    skyCamera.update(renderer, skyScene);
    renderer.toneMapping = toneMapping;
    renderer.toneMappingExposure = exposure;
    scene.background = skyTarget.texture;
  };

  /** Sinh lại ảnh môi trường (PMREM) từ bầu trời vừa nướng. */
  const bakeEnvironment = () => {
    // Tắt đĩa mặt trời lúc render env để không sinh vệt sáng cứng trên model.
    const showSunDisc = uniforms.showSunDisc.value;
    uniforms.showSunDisc.value = 0;
    envTarget?.dispose();
    envTarget = pmrem.fromScene(skyScene, 0, 1, SKY_BOX_SCALE * 2, { size: ENV_SIZE });
    uniforms.showSunDisc.value = showSunDisc;
    scene.environment = envTarget.texture;
    scene.environmentIntensity = ENVIRONMENT_INTENSITY;
  };

  const apply = (preset: HeritageSkyPreset | null) => {
    const turbidity = readNumber(preset?.turbidity) ?? DEFAULTS.turbidity;
    const rayleigh = readNumber(preset?.rayleigh) ?? DEFAULTS.rayleigh;
    const mieCoefficient =
      readNumber(preset?.mieCoefficient) ?? DEFAULTS.mieCoefficient;
    const mieDirectionalG =
      readNumber(preset?.mieDirectionalG) ?? DEFAULTS.mieDirectionalG;
    // Mây: thiếu dữ liệu thì trời quang (0), không lấy mặc định 0.4 của three —
    // preset cũ không có trường này mà tự dưng có mây thì sai hiện trạng.
    const cloudCoverage =
      readNumber(preset?.cloudCoverage) ?? DEFAULTS.cloudCoverage;
    const cloudDensity = readNumber(preset?.cloudDensity) ?? DEFAULTS.cloudDensity;
    const elevation = readNumber(preset?.elevation) ?? DEFAULTS.elevation;
    const azimuth = readNumber(preset?.azimuth) ?? DEFAULTS.azimuth;

    uniforms.turbidity.value = turbidity;
    uniforms.rayleigh.value = rayleigh;
    uniforms.mieCoefficient.value = mieCoefficient;
    uniforms.mieDirectionalG.value = mieDirectionalG;
    uniforms.cloudCoverage.value = cloudCoverage;
    uniforms.cloudDensity.value = cloudDensity;

    // Sky nhận hướng mặt trời bằng toạ độ cầu: elevation 90° = đỉnh đầu.
    const phi = THREE.MathUtils.degToRad(90 - elevation);
    const theta = THREE.MathUtils.degToRad(azimuth);
    uniforms.sunPosition.value.setFromSphericalCoords(1, phi, theta);

    renderer.toneMappingExposure = readNumber(preset?.exposure) ?? DEFAULTS.exposure;

    const lights = readRecord(preset?.light_settings);
    const hemi = readRecord(lights?.hemi);
    hemiLight.color.set(readColor(hemi?.color) ?? DEFAULTS.hemiColor);
    hemiLight.groundColor.set(
      readColor(hemi?.groundColor) ?? DEFAULTS.hemiGroundColor,
    );
    hemiLight.intensity = readNumber(hemi?.intensity) ?? DEFAULTS.hemiIntensity;

    const dir = readRecord(lights?.dir);
    dirLight.color.set(readColor(dir?.color) ?? DEFAULTS.dirColor);
    dirLight.intensity = readNumber(dir?.intensity) ?? DEFAULTS.dirIntensity;
    const dirPosition = readRecord(dir?.position);
    dirLight.position.set(
      readNumber(dirPosition?.x) ?? DEFAULTS.dirPosition[0],
      readNumber(dirPosition?.y) ?? DEFAULTS.dirPosition[1],
      readNumber(dirPosition?.z) ?? DEFAULTS.dirPosition[2],
    );

    // Sương mù chỉ bật khi có CẢ màu lẫn mật độ. Dữ liệu nguồn chỉ cho màu
    // (`light_settings.fog.color`), mật độ nằm ở `threeJS_sets.fog_density` và
    // đang null ⇒ không dựng sương mù thay vì đoán một mật độ sai.
    const fog = readRecord(lights?.fog);
    const fogColor = readColor(fog?.color);
    const fogDensity =
      readNumber(preset?.fogDensity) ?? readNumber(fog?.density);
    scene.fog =
      fogColor && fogDensity ? new THREE.FogExp2(fogColor, fogDensity) : null;

    // Bầu trời chỉ phụ thuộc các uniform ở trên; đèn/phơi sáng/sương mù không ảnh
    // hưởng tới lần nướng. Trùng bộ tham số (s5/s6, s4/s7 dùng chung preset) thì
    // bỏ qua — đổi cảnh không phải nướng lại, không có khựng.
    const signature = [
      turbidity,
      rayleigh,
      mieCoefficient,
      mieDirectionalG,
      cloudCoverage,
      cloudDensity,
      elevation,
      azimuth,
    ].join("|");
    if (signature === bakedSignature) return;
    bakedSignature = signature;
    bakeSky();
    bakeEnvironment();
  };

  apply(null);

  return {
    apply,
    dispose() {
      envTarget?.dispose();
      pmrem.dispose();
      skyTarget.dispose();
      skyScene.remove(sky);
      sky.geometry.dispose();
      (sky.material as THREE.Material).dispose();
      scene.remove(hemiLight, dirLight);
      if (scene.background === skyTarget.texture) scene.background = null;
    },
  };
}

export type Environment = ReturnType<typeof createEnvironment>;
