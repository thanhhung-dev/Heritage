// SPDX-License-Identifier: LicenseRef-Summer-Platform-Restriction-1.1
// Copyright (c) 2026 宋夏天Dazzle
// 作者全平台ID：宋夏天Dazzle；公众号：送你整个夏天
// Source: https://github.com/songsummer920-dazzle/three-scope-map-skill
// Modified for HeritageGraph: map-only scene, Vietnamese geometry and flat fills,
// native React lifecycle. Geometry, side shader, chase ribbon and HUD arcs
// adapted from classic/ZhejiangThreeMap.tsx at f8c9369; no terrain imagery.
import * as THREE from "three";
import type { BoundaryFeature, Coordinate, Polygon } from "./geography";

export const MAP_THEME_PRIMARY = "#ff9b2d";
const accent = new THREE.Color(MAP_THEME_PRIMARY);
const tint = (lightness: number, saturation = 0) => accent.clone().offsetHSL(0, saturation, lightness);
export type Projection = (point: Coordinate) => Coordinate;

function makeShape(rings: Polygon, project: Projection) {
  const points = (ring: Coordinate[]) => ring.map((coord) => {
    const [x, y] = project(coord);
    return new THREE.Vector2(x, y);
  });
  let outer = points(rings[0]);
  if (!THREE.ShapeUtils.isClockWise(outer)) outer = outer.reverse();
  const shape = new THREE.Shape(outer);
  rings.slice(1).forEach((ring) => {
    let hole = points(ring);
    if (THREE.ShapeUtils.isClockWise(hole)) hole = hole.reverse();
    shape.holes.push(new THREE.Path(hole));
  });
  return shape;
}

// Original side-wall gradient, with the same depth/opacity hierarchy.
function createSideGradientMaterial() {
  return new THREE.ShaderMaterial({
    transparent: true, side: THREE.DoubleSide, depthWrite: false,
    uniforms: {
      topColor: { value: accent.clone() }, midColor: { value: tint(-0.18, -0.18) },
      bottomColor: { value: tint(-0.55, -0.35) }, alpha: { value: 0.86 },
      topZ: { value: 44 }, bottomZ: { value: 24 },
    },
    vertexShader: `
      uniform float topZ;
      uniform float bottomZ;
      varying float vDepth;
      void main() {
        vDepth = clamp((position.z - bottomZ) / max(0.001, topZ - bottomZ), 0.0, 1.0);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `
      uniform vec3 topColor;
      uniform vec3 midColor;
      uniform vec3 bottomColor;
      uniform float alpha;
      varying float vDepth;
      void main() {
        vec3 lower = mix(bottomColor, midColor, smoothstep(0.0, 0.24, vDepth));
        vec3 color = mix(lower, topColor, smoothstep(0.34, 1.0, vDepth));
        float edgeGlow = smoothstep(0.48, 1.0, vDepth);
        gl_FragColor = vec4(color + edgeGlow * topColor * 0.24, alpha * (0.46 + vDepth * 0.54));
      }`,
  });
}

function sideWalls(rings: Polygon, project: Projection) {
  const positions: number[] = [], indices: number[] = [];
  for (const ring of rings) for (let i = 0; i < ring.length - 1; i++) {
    const [ax, ay] = project(ring[i]), [bx, by] = project(ring[i + 1]);
    const offset = positions.length / 3;
    positions.push(ax, ay, 44, bx, by, 44, bx, by, 24, ax, ay, 24);
    indices.push(offset, offset + 1, offset + 2, offset, offset + 2, offset + 3);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return new THREE.Mesh(geometry, createSideGradientMaterial());
}

function boundary(rings: Polygon, project: Projection, z: number, opacity: number) {
  const points: THREE.Vector3[] = [];
  for (const ring of rings) for (let i = 0; i < ring.length - 1; i++) {
    for (const coord of [ring[i], ring[i + 1]]) {
      const [x, y] = project(coord);
      points.push(new THREE.Vector3(x, y, z));
    }
  }
  const line = new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(points), new THREE.LineBasicMaterial({
    color: accent, transparent: true, opacity, depthWrite: false,
    blending: THREE.AdditiveBlending,
  }));
  return line;
}

// Chase ribbon from the template. Follow each actual outer ring rather than a
// rasterized silhouette: small islands are retained, and no sea gap is bridged.
function chaseLight(rings: Coordinate[][], project: Projection) {
  const positions: number[] = [], distances: number[] = [], indices: number[] = [];
  let total = 0;
  for (const ring of rings) for (let i = 0; i < ring.length - 1; i++) {
    const [ax, ay] = project(ring[i]), [bx, by] = project(ring[i + 1]);
    const start = new THREE.Vector3(ax, ay, 45), end = new THREE.Vector3(bx, by, 45);
    const length = start.distanceTo(end);
    if (length < 0.01) continue;
    const normal = new THREE.Vector3(-(end.y - start.y), end.x - start.x, 0).normalize().multiplyScalar(0.8);
    const divisions = Math.max(1, Math.ceil(length / 1.35));
    for (let step = 0; step < divisions; step++) {
      const from = start.clone().lerp(end, step / divisions);
      const to = start.clone().lerp(end, (step + 1) / divisions);
      const offset = positions.length / 3;
      [from.clone().add(normal), from.clone().sub(normal), to.clone().add(normal), to.clone().sub(normal)]
        .forEach((point) => positions.push(point.x, point.y, point.z));
      const a = total + length * step / divisions, b = total + length * (step + 1) / divisions;
      distances.push(a, a, b, b);
      indices.push(offset, offset + 1, offset + 2, offset + 2, offset + 1, offset + 3);
    }
    total += length;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  const alpha = new THREE.Float32BufferAttribute(new Float32Array(distances.length), 1);
  geometry.setAttribute("alpha", alpha);
  geometry.setIndex(indices);
  const material = new THREE.ShaderMaterial({
    transparent: true, blending: THREE.AdditiveBlending, depthTest: false,
    depthWrite: false, side: THREE.DoubleSide,
    uniforms: { color: { value: new THREE.Color("#ffffff") } },
    vertexShader: `attribute float alpha; varying float vAlpha;
      void main() { vAlpha = alpha; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `uniform vec3 color; varying float vAlpha;
      void main() { gl_FragColor = vec4(color, vAlpha); }`,
  });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.renderOrder = 20;
  return { mesh, update(time: number) {
    const head = time * 230 % total, tail = Math.max(100, total * 0.07);
    for (let i = 0; i < distances.length; i++) {
      const behind = (head - distances[i] + total) % total;
      alpha.setX(i, behind > tail ? 0 : Math.pow(1 - behind / tail, 1.65));
    }
    alpha.needsUpdate = true;
  } };
}

export function createClassicRegion(feature: BoundaryFeature, project: Projection) {
  const group = new THREE.Group();
  group.userData.region = feature.properties.id;
  const polygons = feature.geometry.coordinates;
  const shapes = polygons.map((polygon) => makeShape(polygon, project));
  const rings = polygons.flat();
  const geometry = new THREE.ShapeGeometry(shapes);
  const fill = new THREE.MeshStandardMaterial({
    color: tint(feature.properties.id === "hue" ? -0.39 : -0.43, -0.65),
    emissive: tint(-0.5, -0.65), emissiveIntensity: 0.1,
    roughness: 0.95, metalness: 0.03, side: THREE.DoubleSide,
  });
  const surface = new THREE.Mesh(geometry, fill);
  surface.position.z = 44;
  surface.userData.region = feature.properties.id;
  group.add(surface, sideWalls(rings, project), boundary(rings, project, 44.3, 0.84), boundary(rings, project, 24, 0.45));
  const base = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ color: tint(-0.55), side: THREE.DoubleSide }));
  base.position.z = 23.9;
  group.add(base);
  const highlightMaterial = new THREE.MeshBasicMaterial({
    color: accent, transparent: true, opacity: 0.045, blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide, depthWrite: false,
  });
  const highlight = new THREE.Mesh(geometry, highlightMaterial);
  highlight.position.z = 44.5;
  group.add(highlight);
  const chase = chaseLight(polygons.map((polygon) => polygon[0]), project);
  group.add(chase.mesh);
  return { group, update(time: number, reduced: boolean) {
    if (!reduced) chase.update(time);
  } };
}

// Same arc layout, radii, tick count and subdued opacity as the classic HUD base.
export function createHudRing() {
  const plate = new THREE.Group(), rotor = new THREE.Group();
  plate.position.z = 12;
  plate.scale.setScalar(0.9);
  plate.add(rotor);
  for (const [inner, outer, opacity] of [[356, 362, 0.055], [244, 248, 0.035]]) {
    rotor.add(new THREE.Mesh(new THREE.RingGeometry(inner, outer, 160), new THREE.MeshBasicMaterial({
      color: accent, transparent: true, opacity, blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide, depthWrite: false,
    })));
  }
  const arcMaterial = new THREE.LineBasicMaterial({ color: accent, transparent: true, opacity: 0.24, depthWrite: false });
  const specs = [[0.1, 0.92, 390], [1.42, 2.04, 390], [2.56, 3.3, 390], [4.1, 4.82, 390],
    [5.22, 5.9, 390], [0.72, 1.34, 316], [2.12, 2.78, 316], [3.56, 4.2, 316],
    [5.02, 5.58, 316], [0.18, 0.62, 252], [3.18, 3.76, 252]];
  for (const [start, end, radius] of specs) {
    const points = Array.from({ length: 73 }, (_, i) => {
      const angle = start + (end - start) * i / 72;
      return new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 2);
    });
    rotor.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), arcMaterial));
  }
  const ticks: THREE.Vector3[] = [];
  for (let i = 0; i < 48; i++) {
    if (i % 4 === 0) continue;
    const angle = Math.PI * 2 * i / 48;
    for (const radius of [344, i % 2 === 0 ? 370 : 362]) ticks.push(new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 3));
  }
  rotor.add(new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(ticks), arcMaterial));
  return { plate, rotor };
}

export function disposeScene(scene: THREE.Scene) {
  const geometries = new Set<THREE.BufferGeometry>(), materials = new Set<THREE.Material>();
  scene.traverse((object) => {
    if (object instanceof THREE.Mesh || object instanceof THREE.Line) {
      geometries.add(object.geometry);
      const values = Array.isArray(object.material) ? object.material : [object.material];
      values.forEach((material) => materials.add(material));
    }
  });
  geometries.forEach((geometry) => geometry.dispose());
  materials.forEach((material) => material.dispose());
  scene.clear();
}
