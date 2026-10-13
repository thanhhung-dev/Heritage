import * as THREE from "three";
import type { HeritageInteractiveHighlight } from "@/types/heritage";
import { toVector3 } from "./camera-controller";

function createBadgeTexture(number: number) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 256;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Không tạo được texture lens badge.");
  const glow = context.createRadialGradient(128, 128, 58, 128, 128, 124);
  glow.addColorStop(0, "rgba(255,255,255,0.5)");
  glow.addColorStop(0.4, "rgba(255,255,255,0.15)");
  glow.addColorStop(1, "rgba(255,255,255,0)");
  context.fillStyle = glow;
  context.fillRect(0, 0, 256, 256);
  context.beginPath();
  context.arc(128, 128, 62, 0, Math.PI * 2);
  context.fillStyle = "rgba(28,27,26,0.8)";
  context.fill();
  context.strokeStyle = "rgba(255,255,255,0.95)";
  context.lineWidth = 4;
  context.stroke();
  context.fillStyle = "#fff";
  context.font = "600 88px Arial";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(String(number), 128, 132);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

/** Badge phẳng có số/glow, đặt trong Group tại vị trí hotspot của tour. */
export function createInteractiveHighlights(scene: THREE.Scene) {
  const group = new THREE.Group();
  group.name = "interactive_hotspots";
  group.visible = false;
  scene.add(group);
  // Nửa ngoài của texture là glow; vòng badge giữ đường kính như marker cũ.
  const geometry = new THREE.PlaneGeometry(0.1, 0.1);
  const markers = new Map<number, THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>>();
  const cameraRotation = new THREE.Quaternion();
  let items: HeritageInteractiveHighlight[] = [];
  const listeners = new Set<(item: HeritageInteractiveHighlight | null) => void>();
  function select(id: number | null) {
    const item = items.find((item) => item.id === id) ?? null;
    markers.forEach((marker, key) => marker.material.color.set(key === item?.id ? "#fff" : "#ff9b2d"));
    listeners.forEach((listener) => listener(item));
  }
  function clear() {
    markers.forEach((marker) => { marker.material.map?.dispose(); marker.material.dispose(); });
    markers.clear();
    group.clear();
    items = [];
    select(null);
  }
  return {
    set(highlights: HeritageInteractiveHighlight[]) {
      clear();
      items = [...highlights].sort((a, b) => a.sort_order - b.sort_order);
      for (const [index, item] of items.entries()) {
        const position = toVector3(item.lens_pos);
        if (!position) continue;
        const hotspot = new THREE.Group();
        hotspot.name = `hotspot_${item.id}`;
        hotspot.position.copy(position);
        const marker = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({
          color: "#ff9b2d", map: createBadgeTexture(index + 1), transparent: true,
          depthTest: false, depthWrite: false, toneMapped: false,
        }));
        marker.name = "lens_badge";
        marker.renderOrder = 100;
        const scale = toVector3(item.lens_scale);
        if (scale) marker.scale.copy(scale);
        marker.userData.highlightId = item.id;
        hotspot.add(marker);
        group.add(hotspot);
        markers.set(item.id, marker);
      }
    },
    update(camera: THREE.Camera) {
      if (!group.visible) return;
      camera.getWorldQuaternion(cameraRotation);
      markers.forEach((marker) => marker.quaternion.copy(cameraRotation));
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
