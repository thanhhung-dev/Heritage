import * as THREE from "three";
import type { HeritageInteractiveHighlight } from "@/types/heritage";
import { toVector3 } from "./camera-controller";

/** Marker cầu cơ bản; lens shader/icon/model tương tác sẽ thay tại đây. */
export function createInteractiveHighlights(scene: THREE.Scene) {
  const group = new THREE.Group();
  group.visible = false;
  scene.add(group);
  const geometry = new THREE.SphereGeometry(0.35, 12, 8);
  const markers = new Map<number, THREE.Mesh<THREE.SphereGeometry, THREE.MeshBasicMaterial>>();
  let items: HeritageInteractiveHighlight[] = [];
  const listeners = new Set<(item: HeritageInteractiveHighlight | null) => void>();
  function select(id: number | null) {
    const item = items.find((item) => item.id === id) ?? null;
    markers.forEach((marker, key) => marker.material.color.set(key === item?.id ? "#fff" : "#ff9b2d"));
    listeners.forEach((listener) => listener(item));
  }
  function clear() {
    markers.forEach((marker) => marker.material.dispose());
    markers.clear();
    group.clear();
    items = [];
    select(null);
  }
  return {
    set(highlights: HeritageInteractiveHighlight[]) {
      clear();
      items = highlights;
      for (const item of items) {
        const position = toVector3(item.lens_pos);
        if (!position) continue;
        const marker = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ color: "#ff9b2d" }));
        marker.position.copy(position);
        const rotation = toVector3(item.lens_rot);
        const scale = toVector3(item.lens_scale);
        if (rotation) marker.rotation.set(rotation.x, rotation.y, rotation.z);
        if (scale) marker.scale.copy(scale);
        marker.userData.highlightId = item.id;
        group.add(marker);
        markers.set(item.id, marker);
      }
    },
    select,
    show: (visible: boolean) => { group.visible = visible; },
    pick(raycaster: THREE.Raycaster) {
      if (!group.visible) return;
      const hit = raycaster.intersectObjects([...markers.values()])[0];
      if (hit) select(hit.object.userData.highlightId as number);
    },
    subscribe(listener: (item: HeritageInteractiveHighlight | null) => void) {
      listeners.add(listener);
      return () => { listeners.delete(listener); };
    },
    dispose() {
      listeners.clear();
      clear();
      geometry.dispose();
      scene.remove(group);
    },
  };
}
