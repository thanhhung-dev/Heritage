import * as THREE from "three";
import type { HeritageSceneHighlight } from "@/types/heritage";
import { toVector3 } from "./camera-controller";
import type { ModelLoader } from "./model-loader";

// Payload hiện chưa có mốc thời gian: adapter phải cung cấp chúng, không tự đoán.
export type TimedSceneHighlight = HeritageSceneHighlight & { startSeconds: number; endSeconds: number };

export function createSceneHighlights(scene: THREE.Scene, loader: ModelLoader, invalidate: () => void) {
  const group = new THREE.Group();
  scene.add(group);
  let revision = 0;
  let entries: { model: THREE.Object3D; item: TimedSceneHighlight; rotationY: number }[] = [];
  return {
    async set(items: TimedSceneHighlight[]) {
      const current = ++revision;
      group.clear();
      entries = [];
      invalidate();
      await Promise.all(items.map(async (item) => {
        const gltf = await loader.load(item.model_url);
        if (current !== revision) return;
        const model = gltf.scene.clone(true);
        const position = toVector3(item.position);
        const rotation = toVector3(item.rotation);
        const scale = toVector3(item.scale);
        if (position) model.position.copy(position);
        if (rotation) model.rotation.set(rotation.x, rotation.y, rotation.z);
        if (scale) model.scale.copy(scale);
        model.visible = false;
        group.add(model);
        entries.push({ model, item, rotationY: model.rotation.y });
        invalidate();
      }));
    },
    update(seconds: number) {
      let changed = false;
      for (const { model, item, rotationY } of entries) {
        const visible = seconds >= item.startSeconds && seconds < item.endSeconds;
        const rotation = rotationY + (item.animation_type === "rotate" ? Math.max(0, seconds - item.startSeconds) : 0);
        changed ||= model.visible !== visible || (visible && model.rotation.y !== rotation);
        model.visible = visible;
        model.rotation.y = rotation;
      }
      return changed;
    },
    dispose() {
      revision++;
      entries = [];
      group.clear();
      scene.remove(group);
      // Geometry/material thuộc cache của loader, không dispose riêng các clone.
    },
  };
}
