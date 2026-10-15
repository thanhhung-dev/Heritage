import * as THREE from "three";
import type { HeritageInteractiveHighlight } from "@/types/heritage";
import { toVector3, type DollyTarget } from "./camera-controller";
import { camLog } from "./camera-debug";

const BADGE_SIZE = 0.37;
const HOVER_SCALE = 1.12;
const ANIM_SPEED = 12;
const SCALE_EPSILON_SQ = 1e-6;

const HOVER_APPROACH = 0.9;
const HOVER_MIN_DISTANCE = 0.6;

function createBadgeTexture(number: number, hovered = false) {
  const SIZE = 1024;
  const C = SIZE / 2;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = SIZE;

  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("Không tạo được texture lens badge.");
  }

  const GLOW_RADIUS = 490;

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
    glow.addColorStop(0.3, "rgba(255, 210, 70, 0)");
    glow.addColorStop(0.4, "rgba(255, 200, 50, 0.1)");
    glow.addColorStop(0.5, "rgba(255, 200, 50, 0.4)");
    glow.addColorStop(0.6, "rgba(255, 180, 30, 0.1)");
    glow.addColorStop(0.7, "rgba(255, 160, 0, 0)");
    glow.addColorStop(1, "rgba(255, 160, 0, 0)");

  } else {
       glow.addColorStop(0, "rgba(255, 220, 80, 0)");
    glow.addColorStop(0.3, "rgba(255, 210, 70, 0)");
    glow.addColorStop(0.4, "rgba(252, 252, 252, 0.1)");
    glow.addColorStop(0.5, "rgba(255, 255, 255, 0.61)");
    glow.addColorStop(0.6, "rgba(249, 249, 249, 0.1)");
    glow.addColorStop(0.7, "rgba(252, 252, 251, 0)");
    glow.addColorStop(1, "rgba(253, 253, 253, 0)");
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

export function createInteractiveHighlights(
  scene: THREE.Scene,
  canvas?: HTMLCanvasElement,
  onHoverTarget?: (target: DollyTarget | null) => void,
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
  let hoveredPoint: THREE.Vector3 | null = null;
  let selectedId: number | null = null;

  function getItem(id: number | null) {
    return items.find((item) => item.id === id) ?? null;
  }

  function refreshTargets() {
    const panelOpen = selectedId !== null;

    markers.forEach((_, key) => {
      const baseScale = baseScales.get(key);
      const target = targetScales.get(key);
      if (!baseScale || !target) return;

      if (panelOpen) {
        target.set(0, 0, 0);
        return;
      }

      target.copy(baseScale).multiplyScalar(key === hoveredId ? HOVER_SCALE : 1);
    });
  }

  function applyHoverTextures(id: number | null) {
    markers.forEach((marker, key) => {
      const material = marker.material;
      material.map =
        key === id ? (hoverTextures.get(key) ?? null) : (normalTextures.get(key) ?? null);
      material.needsUpdate = true;
    });
  }

  function select(id: number | null) {
    const item = getItem(id);
    selectedId = item ? item.id : null;

    if (!item && hoveredId !== null) {
      hoveredId = null;
      applyHoverTextures(null);
    }

    refreshTargets();
    listeners.forEach((listener) => listener(item));
  }

  function setHovered(id: number | null) {
    if (hoveredId === id) return;
    hoveredId = id;
    camLog("badge", `hovered = ${id === null ? "null (rời badge)" : `id=${id}`}`);
    canvas?.style.setProperty("cursor", id === null ? "default" : "pointer");

    refreshTargets();

    applyHoverTextures(id);

    if (!onHoverTarget) return;

    if (id === null) {
      hoveredPoint = null;
      onHoverTarget(null);
      return;
    }

    const marker = markers.get(id);
    if (!marker) {
      onHoverTarget(null);
      return;
    }

    marker.updateWorldMatrix(true, false);
    const point = hoveredPoint ?? (hoveredPoint = new THREE.Vector3());
    marker.getWorldPosition(point);
    onHoverTarget({
      point,
      approach: HOVER_APPROACH,
      minDistance: HOVER_MIN_DISTANCE,
    });
  }

  function hitTest(raycaster: THREE.Raycaster) {
    // Panel đang mở ⇒ mọi badge đang thu về 0: chặn raycast hẳn, nếu không con
    // trỏ vẫn "dính" vào các badge sắp biến mất và camera tiếp tục dí theo chúng.
    if (selectedId !== null) return undefined;

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
    hoveredPoint = null;
    selectedId = null;

    canvas?.style.setProperty("cursor", "default");
    onHoverTarget?.(null);
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

    /**
     * Lerp tỉ lệ badge về đích. Trả về `true` khi còn badge đang chạy animation
     * — vòng render chỉ vẽ khi có gì đó đổi, nên phải báo lại để badge thu nhỏ
     * được vẽ liên tục thay vì đứng hình sau frame đầu.
     */
    update(camera: THREE.Camera, delta = 0.016) {
      if (!group.visible) return false;

      camera.getWorldQuaternion(cameraRotation);

      let animating = false;

      markers.forEach((marker, key) => {
        marker.quaternion.copy(cameraRotation);

        const target = targetScales.get(key);
        if (!target) return;

        marker.scale.lerp(target, Math.min(1, delta * ANIM_SPEED));

        if (marker.scale.distanceToSquared(target) > SCALE_EPSILON_SQ) {
          animating = true;
        }
      });

      return animating;
    },

    select,

    hover(raycaster: THREE.Raycaster) {
      if (!group.visible) {
        setHovered(null);
        return;
      }

      // Panel đang mở ⇒ badge đang ẩn dần. Bỏ qua hẳn thay vì gọi
      // `setHovered(null)`: nhả hover lúc này sẽ đẩy `onHoverTarget(null)` và
      // camera bay ngược về pose cũ ngay sau cú bấm.
      if (selectedId !== null) return;

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

    hoveredId: () => hoveredId,

    selectedId: () => selectedId,

    dispose() {
      listeners.clear();
      clear();
      geometry.dispose();
      scene.remove(group);
    },
  };
}
