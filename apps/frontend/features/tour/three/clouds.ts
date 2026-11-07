import * as THREE from "three";

/** Noise tuần hoàn, nướng một lần trên CPU; shader chỉ lấy mẫu texture, không chạy FBM mỗi pixel. */
function createCloudTexture() {
  const size = 256;
  const pixels = new Uint8Array(size * size);
  const hash = (x: number, y: number) => {
    const value = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
    return value - Math.floor(value);
  };
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      let noise = 0;
      let amplitude = 0.5;
      for (let grid = 4; grid <= 64; grid *= 2) {
        const u = x / size * grid;
        const v = y / size * grid;
        const ix = Math.floor(u);
        const iy = Math.floor(v);
        const fx = u - ix;
        const fy = v - iy;
        const sx = fx * fx * (3 - 2 * fx);
        const sy = fy * fy * (3 - 2 * fy);
        const a = THREE.MathUtils.lerp(hash(ix, iy), hash((ix + 1) % grid, iy), sx);
        const b = THREE.MathUtils.lerp(hash(ix, (iy + 1) % grid), hash((ix + 1) % grid, (iy + 1) % grid), sx);
        noise += THREE.MathUtils.lerp(a, b, sy) * amplitude;
        amplitude *= 0.5;
      }
      pixels[y * size + x] = Math.round(noise / 0.96875 * 255);
    }
  }
  const texture = new THREE.DataTexture(pixels, size, size, THREE.RedFormat);
  texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.generateMipmaps = true;
  texture.needsUpdate = true;
  return texture;
}

/** Lớp mây ở vô cực: không parallax, không che model, không nướng lại trời/PMREM khi trôi. */
export function createClouds(scene: THREE.Scene, background: THREE.CubeTexture) {
  const texture = createCloudTexture();
  const motionPreference = typeof window === "undefined"
    ? null : window.matchMedia("(prefers-reduced-motion: reduce)");
  const interval = typeof window !== "undefined" && window.matchMedia("(max-width: 768px)").matches
    ? 1 / 15 : 1 / 24;
  const material = new THREE.ShaderMaterial({
    uniforms: {
      noiseMap: { value: texture },
      skyMap: { value: background },
      time: { value: 0 },
      coverage: { value: 0 },
      density: { value: 0 },
      sunDirection: { value: new THREE.Vector3(0, 1, 0) },
    },
    vertexShader: /* glsl */`
      varying vec3 vDirection;
      void main() {
        vDirection = position;
        // Bỏ translation của camera, đặt mây ở far plane bất kể tỉ lệ model.
        gl_Position = projectionMatrix * vec4(mat3(viewMatrix) * position, 1.0);
        gl_Position.z = gl_Position.w;
      }
    `,
    fragmentShader: /* glsl */`
      uniform sampler2D noiseMap;
      uniform samplerCube skyMap;
      uniform float time;
      uniform float coverage;
      uniform float density;
      uniform vec3 sunDirection;
      varying vec3 vDirection;
      void main() {
        vec3 direction = normalize(vDirection);
        if (direction.y <= 0.025) discard;
        vec2 uv = direction.xz / max(direction.y, 0.08) * 0.18;
        float large = texture2D(noiseMap, uv + time * vec2(0.0012, 0.0004)).r;
        float detail = texture2D(noiseMap, uv * 2.7 - time * vec2(0.00035, 0.00015)).r;
        float field = smoothstep(0.25, 0.75, large * 0.8 + detail * 0.2);
        float depth = max(field - (1.0 - coverage), 0.0);
        float horizon = smoothstep(0.025, 0.22, direction.y);
        float alpha = (1.0 - exp(-depth * density * 12.0)) * horizon;
        if (alpha < 0.003) discard;
        float daylight = smoothstep(-0.08, 0.3, sunDirection.y);
        vec3 color = mix(vec3(0.015, 0.023, 0.04), vec3(1.5, 1.55, 1.65), daylight);
        float sunset = (1.0 - smoothstep(0.0, 0.3, sunDirection.y)) * daylight;
        color = mix(color, vec3(1.7, 0.85, 0.42), sunset * 0.65);
        color *= mix(0.65, 1.0, field);
        // Haze cùng màu trời thật, không có dải mây trắng cắt ngang chân trời.
        color = mix(textureCube(skyMap, direction).rgb, color, smoothstep(0.025, 0.45, direction.y));
        gl_FragColor = vec4(color, alpha);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
      }
    `,
    side: THREE.BackSide,
    transparent: true,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(2, 2, 2), material);
  mesh.name = "Tour clouds";
  mesh.frustumCulled = false;
  mesh.renderOrder = -1;
  mesh.visible = false;
  scene.add(mesh);
  let elapsed = 0;

  return {
    apply(coverage: number, density: number, sunDirection: THREE.Vector3) {
      material.uniforms.coverage.value = THREE.MathUtils.clamp(coverage, 0, 1);
      material.uniforms.density.value = Math.max(0, density);
      material.uniforms.sunDirection.value.copy(sunDirection).normalize();
      mesh.visible = coverage > 0 && density > 0;
    },
    update(delta: number) {
      if (!mesh.visible || motionPreference?.matches || (typeof document !== "undefined" && document.hidden)) return false;
      elapsed += delta;
      if (elapsed < interval) return false;
      material.uniforms.time.value += elapsed;
      elapsed = 0;
      return true;
    },
    dispose() {
      scene.remove(mesh);
      mesh.geometry.dispose();
      material.dispose();
      texture.dispose();
    },
  };
}
