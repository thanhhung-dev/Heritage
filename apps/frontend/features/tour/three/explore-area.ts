import * as THREE from "three";
import type { ExploreArea } from "@/types/heritage";

const WALL_OFFSET = 0.15;
const WALL_FADE_RATIO = 0.25;
const WALL_TILE_SCALE = 2;
const WALL_OPACITY_EPSILON = 0.002;
const DOT_CELL = 8;
const DOT_SIZE = 2;
const DOT_TILE = DOT_CELL * 4;
const DOT_COLOR = "rgb(251, 217, 148)";

const VERTEX_SHADER = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const DOTS_FRAGMENT_SHADER = `
  uniform float u_opacity;
  uniform vec2 u_hitUV;
  uniform vec2 u_tileScale;
  uniform sampler2D u_texture;
  varying vec2 vUv;
  void main() {
    float dist = distance(vUv, u_hitUV);
    float center = exp(-dist * dist * 3.0);
    float glow = 0.15 + 0.85 * center;
    vec4 tex = texture2D(u_texture, vUv * u_tileScale);
    gl_FragColor = vec4(tex.rgb * glow, tex.a * glow * u_opacity);
  }
`;

export const GLOW_FRAGMENT_SHADER = `
  uniform float u_opacity;
  uniform vec2 u_hitUV;
  varying vec2 vUv;
  void main() {
    float dist = distance(vUv, u_hitUV);
    float center = exp(-dist * dist * 3.0);
    float intensity = 0.15 + 0.85 * center;
    vec3 color = vec3(1.0, 0.5, 0.08);
    gl_FragColor = vec4(color, intensity * u_opacity);
  }
`;

const isVector = (value: unknown, length: number): value is number[] =>
  Array.isArray(value) &&
  value.length === length &&
  value.every((entry) => typeof entry === "number" && Number.isFinite(entry));

export function parseExploreArea(value: unknown): ExploreArea | null {
  if (!value) return null;

  let raw: unknown = value;
  if (typeof raw === "string") {
    try {
      raw = JSON.parse(raw);
    } catch {
      return null;
    }
  }

  if (typeof raw !== "object" || raw === null) return null;

  const { center, extents, rotation } = raw as Partial<ExploreArea>;
  if (!isVector(center, 3) || !isVector(extents, 3) || !isVector(rotation, 4)) {
    return null;
  }
  if (extents.some((entry) => entry <= 0)) return null;

  return { center, extents, rotation };
}

const scratchCenter = new THREE.Vector3();
const scratchQuaternion = new THREE.Quaternion();
const scratchInverse = new THREE.Quaternion();
const scratchLocal = new THREE.Vector3();

function toLocal(point: THREE.Vector3, area: ExploreArea) {
  scratchCenter.set(area.center[0], area.center[1], area.center[2]);
  scratchQuaternion.set(
    area.rotation[0],
    area.rotation[1],
    area.rotation[2],
    area.rotation[3],
  );
  scratchInverse.copy(scratchQuaternion).invert();
  return scratchLocal.copy(point).sub(scratchCenter).applyQuaternion(scratchInverse);
}

export function clampPointToExploreArea(
  point: THREE.Vector3,
  area: ExploreArea,
): boolean {
  const [halfX, halfY, halfZ] = area.extents;
  const local = toLocal(point, area);

  const x = THREE.MathUtils.clamp(local.x, -halfX, halfX);
  const y = THREE.MathUtils.clamp(local.y, -halfY, halfY);
  const z = THREE.MathUtils.clamp(local.z, -halfZ, halfZ);

  if (x === local.x && y === local.y && z === local.z) return false;

  point
    .copy(local.set(x, y, z))
    .applyQuaternion(scratchQuaternion)
    .add(scratchCenter);
  return true;
}

type SideFace = { axis: "x" | "z"; sign: 1 | -1; distance: number };

function nearestSideFace(point: THREE.Vector3, area: ExploreArea): SideFace {
  const local = toLocal(point, area);
  const [halfX, , halfZ] = area.extents;

  const faces: SideFace[] = [
    { axis: "x", sign: 1, distance: halfX - local.x },
    { axis: "x", sign: -1, distance: local.x + halfX },
    { axis: "z", sign: 1, distance: halfZ - local.z },
    { axis: "z", sign: -1, distance: local.z + halfZ },
  ];

  return faces.reduce((best, face) => (face.distance < best.distance ? face : best));
}


function createDotTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = DOT_TILE;

  const context = canvas.getContext("2d");
  if (!context) throw new Error("Không tạo được texture chấm cho tường biên.");

  context.fillStyle = DOT_COLOR;
  for (const offsetX of [-DOT_TILE, 0, DOT_TILE]) {
    for (const offsetY of [-DOT_TILE, 0, DOT_TILE]) {
      for (let y = 0; y < DOT_TILE; y += DOT_CELL) {
        for (let x = 0; x < DOT_TILE; x += DOT_CELL) {
          context.fillRect(
            x - DOT_SIZE / 2 + offsetX,
            y - DOT_SIZE / 2 + offsetY,
            DOT_SIZE,
            DOT_SIZE,
          );
        }
      }
    }
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

export function createExploreBoundary(scene: THREE.Scene) {
  const geometry = new THREE.PlaneGeometry(1, 1);
  const texture = createDotTexture();

  const material = new THREE.ShaderMaterial({
    uniforms: {
      u_opacity: { value: 0 },
      u_hitUV: { value: new THREE.Vector2(0.5, 0.5) },
      u_tileScale: { value: new THREE.Vector2(1, 1) },
      u_texture: { value: texture },
    },
    vertexShader: VERTEX_SHADER,
    fragmentShader: DOTS_FRAGMENT_SHADER,
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
  });

  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = "explore_boundary";
  mesh.renderOrder = 999;
  mesh.frustumCulled = false;
  mesh.visible = false;
  scene.add(mesh);

  const center = new THREE.Vector3();
  const quaternion = new THREE.Quaternion();
  const offset = new THREE.Vector3();
  const gap = new THREE.Vector3();
  const spin = new THREE.Quaternion();
  const yAxis = new THREE.Vector3(0, 1, 0);

  return {
    update(camera: THREE.Camera, area: ExploreArea | null) {
      if (!area) {
        mesh.visible = false;
        return false;
      }

      const [halfX, halfY, halfZ] = area.extents;
      const face = nearestSideFace(camera.position, area);

      const fade = Math.min(halfX, halfZ) * WALL_FADE_RATIO;
      const opacity = 1 - face.distance / fade;

    
      if (opacity <= WALL_OPACITY_EPSILON) {
        mesh.visible = false;
        return false;
      }

      const local = toLocal(camera.position, area);
      let width: number;
      let height: number;
      let hitU: number;
      let hitV: number;

      if (face.axis === "x") {
        offset.set(halfX * face.sign, 0, 0);
        spin.setFromAxisAngle(yAxis, -face.sign * (Math.PI / 2));
        width = halfZ * 2;
        height = halfY * 2;
        hitU = (local.z + halfZ) / (halfZ * 2);
      } else {
        offset.set(0, 0, halfZ * face.sign);
        spin.setFromAxisAngle(yAxis, face.sign === 1 ? 0 : Math.PI);
        width = halfX * 2;
        height = halfY * 2;
        hitU = (local.x + halfX) / (halfX * 2);
      }
      hitV = (local.y + halfY) / (halfY * 2);

      center.set(area.center[0], area.center[1], area.center[2]);
      quaternion.set(
        area.rotation[0],
        area.rotation[1],
        area.rotation[2],
        area.rotation[3],
      );

      gap.set(
        face.axis === "x" ? face.sign * WALL_OFFSET : 0,
        0,
        face.axis === "z" ? face.sign * WALL_OFFSET : 0,
      );
      mesh.position
        .copy(offset)
        .applyQuaternion(quaternion)
        .add(center)
        .add(gap.applyQuaternion(quaternion));
      mesh.quaternion.copy(quaternion).multiply(spin);
      mesh.scale.set(width, height, 1);

      material.uniforms.u_opacity.value = opacity;
      material.uniforms.u_hitUV.value.set(hitU, hitV);
      material.uniforms.u_tileScale.value.set(
        width * WALL_TILE_SCALE,
        height * WALL_TILE_SCALE,
      );
      mesh.visible = true;
      return true;
    },

    show(visible: boolean) {
      mesh.visible = visible;
    },

    dispose() {
      scene.remove(mesh);
      geometry.dispose();
      material.dispose();
      texture.dispose();
    },
  };
}

export type ExploreBoundary = ReturnType<typeof createExploreBoundary>;
