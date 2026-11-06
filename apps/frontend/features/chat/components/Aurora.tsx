"use client";

// Adapted from React Bits Aurora: native WebGL2, without extra dependencies.
import { useEffect, useRef, useState, type CSSProperties } from "react";
import styles from "@/features/chat/components/Aurora.module.css";

const MAX_STOPS = 5;
const MAX_LAYERS = 3;
const INTRO_SECONDS = 2.4;
const VERTEX = `#version 300 es
in vec2 aPosition;
void main() { gl_Position = vec4(aPosition, 0.0, 1.0); }`;
const FRAGMENT = `#version 300 es
precision highp float;
precision highp int;
uniform vec2 uResolution;
uniform float uTime;
uniform vec3 uStops[${MAX_STOPS}];
uniform int uStopCount;
uniform float uAmplitude;
uniform float uBlend;
uniform float uHeight;
uniform float uScale;
uniform float uGlow;
uniform float uBrightness;
uniform int uLayers;
uniform float uFlip;
uniform vec3 uPointer;
uniform float uReveal;
uniform float uOpacity;
uniform float uLightMode;
out vec4 outColor;
vec3 permute(vec3 x) { return mod(((x * 34.0) + 1.0) * x, 289.0); }
float snoise(vec2 v) {
  const vec4 C = vec4(0.211324865405187, 0.366025403784439, -0.577350269189626, 0.024390243902439);
  vec2 i = floor(v + dot(v, C.yy));
  vec2 x0 = v - i + dot(i, C.xx);
  vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
  vec4 x12 = x0.xyxy + C.xxzz;
  x12.xy -= i1;
  i = mod(i, 289.0);
  vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
  vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
  m = m * m;
  m = m * m;
  vec3 x = 2.0 * fract(p * C.www) - 1.0;
  vec3 h = abs(x) - 0.5;
  vec3 ox = floor(x + 0.5);
  vec3 a0 = x - ox;
  m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
  vec3 g;
  g.x = a0.x * x0.x + h.x * x0.y;
  g.yz = a0.yz * x12.xz + h.yz * x12.yw;
  return 130.0 * dot(m, g);
}
float smootherstep(float edge0, float edge1, float x) {
  float t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0);
  return t * t * t * (t * (t * 6.0 - 15.0) + 10.0);
}
vec3 oklabToLinear(vec3 c) {
  float l = c.x + 0.3963377774 * c.y + 0.2158037573 * c.z;
  float m = c.x - 0.1055613458 * c.y - 0.0638541728 * c.z;
  float s = c.x - 0.0894841775 * c.y - 1.2914855480 * c.z;
  l = l * l * l; m = m * m * m; s = s * s * s;
  return vec3(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s);
}
vec3 toSrgb(vec3 c) {
  c = clamp(c, 0.0, 1.0);
  return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(0.0031308, c));
}
vec3 ramp(float t) {
  float x = clamp(t, 0.0, 1.0) * float(uStopCount - 1);
  int i = int(min(floor(x), float(uStopCount - 2)));
  float f = x - float(i);
  f = f * f * (3.0 - 2.0 * f);
  vec3 lch = mix(uStops[i], uStops[i + 1], f);
  lch.x = mix(lch.x, min(lch.x, 0.7), uLightMode);
  return toSrgb(oklabToLinear(vec3(lch.x, lch.y * cos(lch.z), lch.y * sin(lch.z))));
}
float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}
void main() {
  vec2 frag = gl_FragCoord.xy;
  float y = 1.0 - frag.y / uResolution.y;
  y = mix(y, 1.0 - y, uFlip);
  float u = frag.x / uResolution.x;
  float X = (frag.x - uResolution.x * 0.5) / uResolution.y;
  float t = uTime;
  float reach = uPointer.z * exp(-pow((X - uPointer.x) / 0.38, 2.0));
  vec3 glow = vec3(0.0);
  float cover = 0.0;
  for (int k = 0; k < ${MAX_LAYERS}; k++) {
    if (k >= uLayers) break;
    float layer = float(k);
    float seed = layer * 13.7;
    float pace = t * (1.0 - layer * 0.18);
    float warp = snoise(vec2(X * 0.55 * uScale + pace * 0.08 + seed, pace * 0.14 + seed));
    float wave = snoise(vec2(X * 0.85 * uScale + warp * 0.65 - pace * 0.11 + seed, pace * 0.18 - seed)) * 0.68
      + snoise(vec2(X * 1.75 * uScale + warp * 0.85 + pace * 0.15 - seed, pace * 0.24 + seed * 0.5)) * 0.32;
    float hem = uHeight + layer * 0.08 + wave * 0.28 * uAmplitude;
    hem += reach * 0.08 * (layer < 0.5 ? 1.0 : 0.4);
    hem = mix(-0.25, hem, uReveal);
    float soft = (0.04 + uBlend * 0.16) * (1.0 + layer * 0.9);
    float rise = hem - y;
    float low = -soft - uGlow * 0.14;
    float high = 0.26 + soft * 0.6;
    float body = pow(smootherstep(low, high, rise), 1.5 + uGlow * 0.6);
    float lobes = 0.72 + 0.28 * snoise(vec2(X * 1.1 * uScale - pace * 0.09 + seed, y * 0.45 + pace * 0.14));
    float alpha = body * lobes * (layer < 0.5 ? 1.0 : 0.42 / layer);
    alpha = clamp(alpha * (1.0 + reach * 0.25 * smootherstep(0.9, 0.0, abs(y - hem))), 0.0, 1.0);
    vec3 tint = ramp(u + 0.14 * sin(pace * 0.22 + layer * 2.3) + layer * 0.12 + max(rise, 0.0) * 0.08);
    glow = 1.0 - (1.0 - glow) * (1.0 - tint * alpha);
    cover = 1.0 - (1.0 - cover) * (1.0 - alpha);
  }
  float fade = smootherstep(0.0, 0.7, uReveal) * uOpacity;
  float strength = clamp(uBrightness, 0.0, 2.0);
  glow *= fade * min(strength, 1.0);
  cover *= fade * min(strength, 1.0);
  glow = 1.0 - pow(1.0 - glow, vec3(max(strength, 1.0)));

  // Fine static Dot Matrix texture illuminated smoothly by the Simplex Noise Aurora
  float cellSize = 7.5;
  vec2 cellUv = fract(frag / cellSize) - 0.5;
  float dist = length(cellUv);
  float dotMask = 1.0 - smoothstep(0.18, 0.31, dist);
  float matrixMix = mix(0.42, 1.28, dotMask);
  glow = clamp(glow * matrixMix, 0.0, 1.0);
  cover = clamp(cover * mix(0.48, 1.18, dotMask), 0.0, 1.0);

  float dither = (hash(frag) - 0.5) / 255.0;
  if (uLightMode > 0.5) {
    vec3 tint = cover > 0.0001 ? glow / cover : vec3(0.0);
    cover *= smootherstep(0.0, 0.25, cover);
    float alpha = cover * 0.7;
    outColor = vec4(tint * alpha + dither, clamp(alpha + dither, 0.0, 1.0));
    return;
  }
  outColor = vec4(glow + dither, clamp(cover + dither, 0.0, 1.0));
}`;

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const toOklch = (rgb: number[]) => {
  const [r, g, b] = rgb.map(c => c <= .04045 ? c / 12.92 : Math.pow((c + .055) / 1.055, 2.4));
  const l = Math.cbrt(.4122214708 * r + .5363325363 * g + .0514459929 * b);
  const m = Math.cbrt(.2119034982 * r + .6806995451 * g + .1073969566 * b);
  const s = Math.cbrt(.0883024619 * r + .2817188376 * g + .6299787005 * b);
  const a = 1.9779984951 * l - 2.428592205 * m + .4505937099 * s;
  const bLab = .0259040371 * l + .7827717662 * m - .808675766 * s;
  return [.2104542553 * l + .793617785 * m - .0040720468 * s, Math.hypot(a, bLab), Math.atan2(bLab, a)];
};
const unwrapHues = (stops: number[][]) => {
  const known = stops.findIndex(stop => stop[1] > .02);
  let previous = known === -1 ? 0 : stops[known][2];
  return stops.map(stop => {
    let hue = stop[1] > .02 ? stop[2] : previous;
    while (hue - previous > Math.PI) hue -= Math.PI * 2;
    while (hue - previous < -Math.PI) hue += Math.PI * 2;
    previous = hue;
    return [stop[0], stop[1], hue];
  });
};
const compile = (gl: WebGL2RenderingContext, type: number, source: string) => {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (gl.getShaderParameter(shader, gl.COMPILE_STATUS)) return shader;
  gl.deleteShader(shader);
  return null;
};
const link = (gl: WebGL2RenderingContext) => {
  const vertex = compile(gl, gl.VERTEX_SHADER, VERTEX);
  const fragment = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT);
  const program = gl.createProgram();
  if (!vertex || !fragment || !program) {
    gl.deleteShader(vertex); gl.deleteShader(fragment); gl.deleteProgram(program);
    return null;
  }
  gl.attachShader(program, vertex); gl.attachShader(program, fragment);
  gl.bindAttribLocation(program, 0, "aPosition");
  gl.linkProgram(program);
  gl.deleteShader(vertex); gl.deleteShader(fragment);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) { gl.deleteProgram(program); return null; }
  const uniforms: Record<string, WebGLUniformLocation | null> = {};
  const count = gl.getProgramParameter(program, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < count; i++) {
    const info = gl.getActiveUniform(program, i);
    if (info) uniforms[info.name.replace("[0]", "")] = gl.getUniformLocation(program, info.name);
  }
  return { program, uniforms };
};

interface AuroraProps {
  colorStops?: string[];
  amplitude?: number;
  blend?: number;
  height?: number;
  speed?: number;
  scale?: number;
  glow?: number;
  brightness?: number;
  layers?: number;
  direction?: "top" | "bottom";
  mouseInteraction?: boolean;
  intro?: boolean;
  opacity?: number;
  lightMode?: boolean;
  time?: number;
  paused?: boolean;
  dpr?: number;
  className?: string;
  style?: CSSProperties;
}

export default function Aurora({ colorStops = ["#5227FF", "#7cff67", "#5227FF"], amplitude = 1,
  blend = .5, speed = 1, time, height = .45, scale = 1, glow = .6, brightness = 1,
  layers = 1, direction = "top", mouseInteraction = true, intro = true, opacity = 1,
  lightMode = false, paused = false, dpr, className = "", style }: AuroraProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wakeRef = useRef<(() => void) | null>(null);
  const [ready, setReady] = useState(false);
  const stops = colorStops.filter(Boolean).slice(0, MAX_STOPS);
  const settings = {
    stops: stops.length >= 2 ? stops : stops.length === 1 ? [stops[0], stops[0]] : ["#5227FF", "#7cff67"],
    amplitude: Math.max(0, amplitude), blend: clamp(blend, 0, 1), speed, time,
    height: clamp(height, 0, 1), scale: Math.max(.1, scale), glow: Math.max(0, glow),
    brightness: Math.max(0, brightness), layers: clamp(Math.round(layers), 1, MAX_LAYERS),
    flip: direction === "bottom" ? 1 : 0, mouseInteraction, intro, opacity: clamp(opacity, 0, 1),
    lightMode, paused, dpr
  };
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    const gl = canvas?.getContext("webgl2", { alpha: true, premultipliedAlpha: true, antialias: false, depth: false, stencil: false });
    if (!container || !canvas || !gl) return;
    const program = link(gl);
    if (!program) return;
    const u = program.uniforms;
    const buffer = gl.createBuffer();
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    const probe = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    let reduce = media.matches;
    const cache = new Map<string, number[]>();
    const parse = (value: string) => {
      const cached = cache.get(value);
      if (cached) return cached;
      let rgb = [1, 1, 1];
      if (probe) {
        probe.clearRect(0, 0, 1, 1); probe.fillStyle = "#ffffff"; probe.fillStyle = value;
        probe.fillRect(0, 0, 1, 1);
        const [r, g, b] = probe.getImageData(0, 0, 1, 1).data;
        rgb = [r / 255, g / 255, b / 255];
      }
      cache.set(value, rgb);
      return rgb;
    };
    const palette = new Float32Array(MAX_STOPS * 3);
    const view = { width: 1, height: 1 };
    const pointer = { x: 0, inside: false };
    const state = { clock: 0, px: 0, reach: 0, reveal: settingsRef.current.intro && !reduce ? 0 : 1 };
    let raf = 0;
    let last = 0;
    let visible = true;
    let lost = false;
    const render = () => {
      if (lost) return;
      const s = settingsRef.current;
      unwrapHues(s.stops.map(value => toOklch(parse(value)))).forEach((stop, index) => palette.set(stop, index * 3));
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.useProgram(program.program); gl.bindVertexArray(vao);
      gl.uniform2f(u.uResolution, canvas.width, canvas.height);
      gl.uniform1f(u.uTime, s.time !== undefined ? s.time * s.speed * .1 : state.clock);
      gl.uniform3fv(u.uStops, palette); gl.uniform1i(u.uStopCount, s.stops.length);
      gl.uniform1f(u.uAmplitude, s.amplitude); gl.uniform1f(u.uBlend, s.blend);
      gl.uniform1f(u.uHeight, s.height); gl.uniform1f(u.uScale, s.scale);
      gl.uniform1f(u.uGlow, s.glow); gl.uniform1f(u.uBrightness, s.brightness);
      gl.uniform1i(u.uLayers, s.layers); gl.uniform1f(u.uFlip, s.flip);
      gl.uniform3f(u.uPointer, state.px, 0, state.reach);
      gl.uniform1f(u.uReveal, 1 - Math.pow(1 - state.reveal, 3));
      gl.uniform1f(u.uOpacity, s.opacity); gl.uniform1f(u.uLightMode, s.lightMode ? 1 : 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };
    const frame = (now: number) => {
      raf = 0;
      if (!visible || document.hidden || lost) return;
      const s = settingsRef.current;
      const dt = last ? clamp((now - last) / 1000, .0005, .05) : 1 / 60;
      last = now;
      if (s.paused || reduce) {
        state.reveal = 1; state.reach = 0; render(); last = 0; return;
      }
      state.clock += dt * s.speed;
      const engaged = s.mouseInteraction && pointer.inside;
      if (engaged) state.px += ((pointer.x - view.width / 2) / view.height - state.px) * (1 - Math.exp(-dt / .6));
      state.reach += ((engaged ? 1 : 0) - state.reach) * (1 - Math.exp(-dt / (engaged ? .9 : 1.4)));
      state.reveal = !s.intro ? 1 : Math.min(1, state.reveal + dt / INTRO_SECONDS);
      render();
      raf = requestAnimationFrame(frame);
    };
    const wake = () => {
      if (!raf && visible && !document.hidden && !lost) raf = requestAnimationFrame(frame);
    };
    const resize = () => {
      const s = settingsRef.current;
      view.width = Math.max(1, container.clientWidth); view.height = Math.max(1, container.clientHeight);
      const ratio = Math.min(s.dpr || window.devicePixelRatio || 1, 2);
      canvas.width = Math.max(1, Math.round(view.width * ratio));
      canvas.height = Math.max(1, Math.round(view.height * ratio));
      render(); wake();
    };
    const onPointerMove = (event: PointerEvent) => {
      const rect = container.getBoundingClientRect();
      pointer.x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      pointer.inside = pointer.x >= 0 && y >= 0 && pointer.x <= rect.width && y <= rect.height;
      if (!settingsRef.current.paused) wake();
    };
    const onPointerUp = (event: PointerEvent) => { if (event.pointerType !== "mouse") pointer.inside = false; };
    const onPointerLeave = () => { pointer.inside = false; };
    const onVisibility = () => { last = 0; wake(); };
    const onReduce = () => { reduce = media.matches; last = 0; wake(); };
    const onLost = () => { lost = true; cancelAnimationFrame(raf); raf = 0; setReady(false); };
    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);
    const intersection = new IntersectionObserver(entries => {
      visible = entries.some(entry => entry.isIntersecting);
      if (visible) { last = 0; wake(); }
    });
    intersection.observe(container);
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("pointerdown", onPointerMove, { passive: true });
    window.addEventListener("pointerup", onPointerUp, { passive: true });
    window.addEventListener("pointercancel", onPointerUp, { passive: true });
    document.documentElement.addEventListener("pointerleave", onPointerLeave);
    document.addEventListener("visibilitychange", onVisibility);
    media.addEventListener("change", onReduce);
    canvas.addEventListener("webglcontextlost", onLost);
    resize(); setReady(true);
    let lastDpr = settingsRef.current.dpr;
    wakeRef.current = () => {
      if (settingsRef.current.dpr !== lastDpr) { lastDpr = settingsRef.current.dpr; resize(); return; }
      if (!raf) render();
      wake();
    };
    return () => {
      cancelAnimationFrame(raf); wakeRef.current = null;
      resizeObserver.disconnect(); intersection.disconnect();
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerdown", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerUp);
      document.documentElement.removeEventListener("pointerleave", onPointerLeave);
      document.removeEventListener("visibilitychange", onVisibility);
      media.removeEventListener("change", onReduce);
      canvas.removeEventListener("webglcontextlost", onLost);
      gl.deleteProgram(program.program); gl.deleteBuffer(buffer); gl.deleteVertexArray(vao);
      // Release detached contexts without breaking React Strict Mode's setup/cleanup replay.
      queueMicrotask(() => {
        if (!canvas.isConnected) gl.getExtension("WEBGL_lose_context")?.loseContext();
      });
    };
  }, []);
  useEffect(() => { wakeRef.current?.(); });
  return <div ref={containerRef} data-aurora data-ready={ready} data-direction={direction}
    className={`${styles.container} ${className}`}
    style={{ "--aurora-start": settings.stops[0], "--aurora-end": settings.stops[settings.stops.length - 1], ...style } as CSSProperties}
    aria-hidden="true">
    <canvas ref={canvasRef} className={styles.canvas} />
  </div>;
}
