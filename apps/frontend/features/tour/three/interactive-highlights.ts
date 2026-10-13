import * as THREE from "three";
import type { HeritageInteractiveHighlight } from "@/types/heritage";
import { toVector3 } from "./camera-controller";

const BADGE_SIZE = 0.37;
const HOVER_SCALE = 1.12;
const ANIM_SPEED = 12;

function createBadgeTexture(number: number, hovered = false) {
  const SIZE = 1024;
  const C = SIZE / 2;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = SIZE;

  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("Không tạo được texture lens badge.");
  }

  const GLOW_RADIUS = 350;

  const glow = context.createRadialGradient(
    C,
    C,
    0,
    C,
    C,
    GLOW_RADIUS,
  );

  if (hovered) {
    glow.addColorStop(0, "rgba(255, 220, 80, 0)");
    glow.addColorStop(0.3, "rgba(255, 210, 70, 0.06)");
    glow.addColorStop(0.5, "rgba(255, 200, 50, 0.4)");
    glow.addColorStop(1, "rgba(255, 180, 30, 0.06)");
    glow.addColorStop(1, "rgba(255, 160, 0, 0)");

  } else {
    glow.addColorStop(0, "rgba(255,255,255,0)");
    glow.addColorStop(1, "rgba(255,255,255,0.08)");
    glow.addColorStop(0.5, "rgba(255,255,255,0.4)");
    glow.addColorStop(0.7, "rgba(255,255,255,0.25)");
    glow.addColorStop(1, "rgba(255,255,255,0)");
  }

  context.fillStyle = glow;
  context.fillRect(0, 0, SIZE, SIZE);

  context.beginPath();
  context.arc(C, C, 250, 0, Math.PI * 2);
  context.fillStyle = "rgba(252,250,248,0)";
  context.fill();

  context.strokeStyle = "rgba(255,255,255,0.95)";
  context.lineWidth = 16;
  context.stroke();

  context.fillStyle = "#fff";
  context.font = "600 352px Arial";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(String(number), C, C + 16);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;

  return texture;
}

/** Badge số/glow tại vị trí hotspot của tour. */
export function createInteractiveHighlights(
  scene: THREE.Scene,
  canvas?: HTMLCanvasElement,
) {
  const group = new THREE.Group();
  group.name = "interactive_hotspots";
  group.visible = false;
  scene.add(group);

  const geometry = new THREE.PlaneGeometry(BADGE_SIZE, BADGE_SIZE);
  const markers = new Map<
    number,
    THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>
  >();
  const baseScales = new Map<number, THREE.Vector3>();
  const targetScales = new Map<number, THREE.Vector3>();
  const normalTextures = new Map<number, THREE.CanvasTexture>();
  const hoverTextures = new Map<number, THREE.CanvasTexture>();
  const cameraRotation = new THREE.Quaternion();
  const listeners = new Set<
    (item: HeritageInteractiveHighlight | null) => void
  >();

  let items: HeritageInteractiveHighlight[] = [];
  let hoveredId: number | null = null;

  function getItem(id: number | null) {
    return items.find((item) => item.id === id) ?? null;
  }

  function select(id: number | null) {
    const item = getItem(id);
    listeners.forEach((listener) => listener(item));
  }

  function setHovered(id: number | null) {
    if (hoveredId === id) return;
    hoveredId = id;
    canvas?.style.setProperty("cursor", id === null ? "default" : "pointer");

    markers.forEach((marker, key) => {
      const baseScale = baseScales.get(key);
      if (!baseScale) return;

      const target = targetScales.get(key);
      if (!target) return;

      const isHovered = key === id;

      target.copy(baseScale).multiplyScalar(isHovered ? HOVER_SCALE : 1);

      const material = marker.material;
      const hoverTexture = hoverTextures.get(key) ?? null;
      const normalTexture = normalTextures.get(key) ?? null;

      material.map = isHovered ? hoverTexture : normalTexture;
      material.needsUpdate = true;
    });
  }

  function hitTest(raycaster: THREE.Raycaster) {
    return raycaster
      .intersectObjects([...markers.values()])
      .find(
        ({ uv }) => uv && Math.hypot(uv.x - 0.5, uv.y - 0.5) < 496 / 1024,
      );
  }

  function clear() {
    markers.forEach((marker) => {
      marker.material.map?.dispose();
      marker.material.dispose();
    });

    normalTextures.forEach((texture) => texture.dispose());
    hoverTextures.forEach((texture) => texture.dispose());

    markers.clear();
    baseScales.clear();
    targetScales.clear();
    normalTextures.clear();
    hoverTextures.clear();
    group.clear();
    items = [];
    hoveredId = null;

    canvas?.style.setProperty("cursor", "default");
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

        const normalTexture = createBadgeTexture(index + 1, false);
        const hoverTexture = createBadgeTexture(index + 1, true);

        normalTextures.set(item.id, normalTexture);
        hoverTextures.set(item.id, hoverTexture);

        const marker = new THREE.Mesh(
          geometry,
          new THREE.MeshBasicMaterial({
            color: "#ffffff",
            map: normalTexture,
            transparent: true,
            depthTest: false,
            depthWrite: false,
            toneMapped: false,
          }),
        );

        marker.name = "lens_badge";
        marker.renderOrder = 100;

        const scale = toVector3(item.lens_scale);
        if (scale) marker.scale.copy(scale);

        baseScales.set(item.id, marker.scale.clone());
        targetScales.set(item.id, marker.scale.clone());
        marker.userData.highlightId = item.id;

        hotspot.add(marker);
        group.add(hotspot);
        markers.set(item.id, marker);
      }
    },

    update(camera: THREE.Camera, delta = 0.016) {
      if (!group.visible) return;

      camera.getWorldQuaternion(cameraRotation);

      markers.forEach((marker, key) => {
        marker.quaternion.copy(cameraRotation);

        const target = targetScales.get(key);
        if (!target) return;

        marker.scale.lerp(target, Math.min(1, delta * ANIM_SPEED));
      });
    },

    select,

    /** Gọi hàm này khi pointer di chuyển để cập nhật hover. */
    hover(raycaster: THREE.Raycaster) {
      if (!group.visible) {
        setHovered(null);
        return;
      }

      const hit = hitTest(raycaster);
      const id = hit ? (hit.object.userData.highlightId as number) : null;

      setHovered(id);
    },

    show(visible: boolean) {
      group.visible = visible;

      if (!visible) {
        setHovered(null);
      }
    },

    pick(raycaster: THREE.Raycaster) {
      if (!group.visible) return;

      const hit = hitTest(raycaster);
      if (hit) {
        select(hit.object.userData.highlightId as number);
      }
    },

    subscribe(listener: (item: HeritageInteractiveHighlight | null) => void) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },

    dispose() {
      listeners.clear();
      clear();
      geometry.dispose();
      scene.remove(group);
    },
  };
}
