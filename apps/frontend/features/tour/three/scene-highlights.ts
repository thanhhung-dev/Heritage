import * as THREE from "three";
import { clone } from "three/addons/utils/SkeletonUtils.js";
import type { HeritageSceneHighlight } from "@/types/heritage";
import { toVector3 } from "./camera-controller";
import type { ModelLoader } from "./model-loader";

// Payload hiện chưa có mốc thời gian: adapter phải cung cấp chúng, không tự đoán.
export type TimedSceneHighlight = HeritageSceneHighlight & { startSeconds: number; endSeconds: number | null };

export function createSceneHighlights(scene: THREE.Scene, loader: ModelLoader, invalidate: () => void) {
  const group = new THREE.Group();
  scene.add(group);
  let revision = 0;
  let entries: { model: THREE.Object3D; item: TimedSceneHighlight; rotationY: number; mixer: THREE.AnimationMixer | null; time: number }[] = [];
  function clear() {
    entries.forEach(({ mixer, model }) => { mixer?.stopAllAction(); mixer?.uncacheRoot(model); });
    group.clear();
    entries = [];
  }
  return {
    async set(items: TimedSceneHighlight[]) {
      const current = ++revision;
      clear();
      invalidate();
      await Promise.all(items.map(async (item) => {
        const gltf = await loader.load(item.model_url);
        if (current !== revision) return;
        const model = clone(gltf.scene);
        const position = toVector3(item.position);
        const rotation = toVector3(item.rotation);
        const scale = toVector3(item.scale);
        if (position) model.position.copy(position);
        if (rotation) model.rotation.set(rotation.x, rotation.y, rotation.z);
        if (scale) model.scale.copy(scale);
        model.visible = false;
        group.add(model);
        const mixer = item.animation_type === "LoopRepeat" && gltf.animations?.length ? new THREE.AnimationMixer(model) : null;
        gltf.animations?.forEach((clip) => mixer?.clipAction(clip).setLoop(THREE.LoopRepeat, Infinity).play());
        entries.push({ model, item, rotationY: model.rotation.y, mixer, time: -1 });
        invalidate();
      }));
    },
    update(seconds: number) {
      let changed = false;
      for (const entry of entries) {
        const { model, item, rotationY, mixer } = entry;
        const visible = seconds >= item.startSeconds && (item.endSeconds === null || seconds < item.endSeconds);
        const time = Math.max(0, seconds - item.startSeconds);
        const rotation = rotationY + (item.animation_type === "rotate" ? Math.max(0, seconds - item.startSeconds) : 0);
        changed ||= model.visible !== visible || (visible && (model.rotation.y !== rotation || (mixer !== null && entry.time !== time)));
        model.visible = visible;
        model.rotation.y = rotation;
        mixer?.setTime(time);
        entry.time = time;
      }
      return changed;
    },
    dispose() {
      revision++;
      clear();
      scene.remove(group);
      // Geometry/material thuộc cache của loader, không dispose riêng các clone.
    },
  };
}
