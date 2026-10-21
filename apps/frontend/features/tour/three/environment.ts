import * as THREE from "three";
import type { HeritageSkyPreset } from "@/types/heritage";

/** Môi trường cơ bản. Sky vật lý và light_settings sẽ được bổ sung tại đây. */
export function setupEnvironment(scene: THREE.Scene, renderer: THREE.WebGLRenderer, preset?: HeritageSkyPreset | null) {
  scene.background = new THREE.Color("#1c1b1a");
  if (preset?.exposure != null) renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = preset?.exposure ?? 1;
  scene.add(new THREE.HemisphereLight(0xffffff, 0x72726b, 2));
  const light = new THREE.DirectionalLight(0xffffff, 2);
  light.position.set(1, 2, 1);
  scene.add(light);
}
