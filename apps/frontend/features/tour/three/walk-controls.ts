/**
 * Điều khiển đi bộ: bàn phím WASD + "cần gạt ảo" bằng cách kéo trên canvas.
 *
 * Bản gốc Tapestry chuẩn hoá độ dịch chuyển kéo về `[-1, 1]` TRƯỚC khi dùng:
 * phép quay là `-x * 90°/giây * dt`, nếu `x` là số pixel thô thì một cú kéo 5px
 * đã quay hơn 400°/giây — vô lý. Nên đây là cần gat neo tại điểm bấm (kéo càng
 * xa càng nhanh, tối đa ở `DRAG_RADIUS`), không phải cộng dồn delta từng frame.
 */

/** Vùng chết cho cả hai trục (gốc `qT`). */
export const INPUT_DEAD_ZONE = 0.15;
/** Kéo đủ xa này thì cần gạt đạt biên độ tối đa (px). */
export const DRAG_RADIUS = 110;
/** Tốc độ quay khi cần gạt ở biên (gốc `KR`). */
export const TURN_SPEED_DEG_PER_SECOND = 90;
/** Tốc độ đi (gốc `jR`). */
export const WALK_SPEED = 5;

const MOVE_KEYS = new Set(["w", "a", "s", "d"]);

export interface WalkInput {
  /** Tiến/lui, dương là đi tới. */
  forward: number;
  /** Sang ngang, dương là sang phải. */
  strafe: number;
  /** Quay, dương là quay sang phải. Đã áp vùng chết, trong `[-1, 1]`. */
  turn: number;
}

const isEditable = (target: EventTarget | null) => {
  if (!(target instanceof HTMLElement)) return false;
  const tag = target.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || target.isContentEditable;
};

export function createWalkInput(canvas: HTMLElement) {
  const keys = new Set<string>();
  const drag = { x: 0, y: 0 };
  /**
   * Cần gạt ảo trên màn hình (mobile). Không phải pointer event trên canvas nên
   * không đi qua `drag`; React đẩy giá trị đã chuẩn hoá `[-1, 1]` vào đây.
   */
  const stick = { x: 0, y: 0, active: false };
  let pointerId: number | null = null;
  let originX = 0;
  let originY = 0;
  let attached = false;

  const onKeyDown = (event: KeyboardEvent) => {
    if (event.metaKey || event.ctrlKey || event.altKey || isEditable(event.target)) return;
    const key = event.key.toLowerCase();
    if (MOVE_KEYS.has(key)) keys.add(key);
  };

  const onKeyUp = (event: KeyboardEvent) => {
    keys.delete(event.key.toLowerCase());
  };

  // Mất focus giữa chừng (đổi tab, mở hộp thoại) sẽ nuốt luôn keyup ⇒ kẹt phím.
  const onBlur = () => keys.clear();

  const onPointerDown = (event: PointerEvent) => {
    if (pointerId !== null) return;
    pointerId = event.pointerId;
    originX = event.clientX;
    originY = event.clientY;
    drag.x = 0;
    drag.y = 0;
    // Giữ được cần gạt cả khi con trỏ kéo ra ngoài canvas.
    canvas.setPointerCapture?.(event.pointerId);
  };

  const onPointerMove = (event: PointerEvent) => {
    if (event.pointerId !== pointerId) return;
    drag.x = Math.max(-1, Math.min(1, (event.clientX - originX) / DRAG_RADIUS));
    drag.y = Math.max(-1, Math.min(1, (event.clientY - originY) / DRAG_RADIUS));
  };

  const release = (event: PointerEvent) => {
    if (event.pointerId !== pointerId) return;
    pointerId = null;
    drag.x = 0;
    drag.y = 0;
    canvas.releasePointerCapture?.(event.pointerId);
  };

  return {
    attach() {
      if (attached) return;
      attached = true;
      window.addEventListener("keydown", onKeyDown);
      window.addEventListener("keyup", onKeyUp);
      window.addEventListener("blur", onBlur);
      canvas.addEventListener("pointerdown", onPointerDown);
      canvas.addEventListener("pointermove", onPointerMove);
      canvas.addEventListener("pointerup", release);
      canvas.addEventListener("pointercancel", release);
    },

    detach() {
      if (!attached) return;
      attached = false;
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
      window.removeEventListener("blur", onBlur);
      canvas.removeEventListener("pointerdown", onPointerDown);
      canvas.removeEventListener("pointermove", onPointerMove);
      canvas.removeEventListener("pointerup", release);
      canvas.removeEventListener("pointercancel", release);
      keys.clear();
      drag.x = 0;
      drag.y = 0;
      pointerId = null;
    },

    /** Xoá sạch input — gọi khi vào/ra chế độ để không giữ lại phím cũ. */
    clear() {
      keys.clear();
      drag.x = 0;
      drag.y = 0;
      stick.x = 0;
      stick.y = 0;
      stick.active = false;
    },

    /**
     * Cần gạt ảo: toạ độ đã chuẩn hoá `[-1, 1]`, gốc ở tâm, y dương là kéo XUỐNG
     * (lùi) — cùng quy ước với `drag`.
     */
    setStick(x: number, y: number) {
      stick.x = Math.max(-1, Math.min(1, x));
      stick.y = Math.max(-1, Math.min(1, y));
      stick.active = true;
    },

    /** Nhả cần gạt: dừng di chuyển ngay, không giữ quán tính. */
    releaseStick() {
      stick.x = 0;
      stick.y = 0;
      stick.active = false;
    },

    read(): WalkInput {
      let forward = 0;
      let strafe = 0;

      if (keys.has("w")) forward += 1;
      if (keys.has("s")) forward -= 1;
      if (keys.has("d")) strafe += 1;
      if (keys.has("a")) strafe -= 1;

      // Trục dọc của cần gạt đẩy tiến/lui. Kéo XUỐNG là lùi, giống bản gốc
      // (`gs.add(Wt * -t.y)`).
      if (Math.abs(drag.y) >= INPUT_DEAD_ZONE) forward -= drag.y;

      // Cần gạt ảo (mobile): dọc = tiến/lùi, ngang = QUAY camera. Trục ngang
      // cộng dồn với cú kéo trên canvas rồi kẹp `[-1, 1]` để hai nguồn cùng
      // đẩy một hướng không thành quay gấp đôi.
      if (stick.active && Math.abs(stick.y) >= INPUT_DEAD_ZONE) forward -= stick.y;

      let turn = Math.abs(drag.x) >= INPUT_DEAD_ZONE ? drag.x : 0;
      if (stick.active && Math.abs(stick.x) >= INPUT_DEAD_ZONE) turn += stick.x;
      turn = Math.max(-1, Math.min(1, turn));

      return { forward, strafe, turn };
    },
  };
}

export type WalkInputSource = ReturnType<typeof createWalkInput>;
