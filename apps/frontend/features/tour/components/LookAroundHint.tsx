"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import styles from "../styles.module.css";

/** Kéo quá ngưỡng này mới tính là "đã xoay", trước đó coi như bấm nhầm. */
const DRAG_THRESHOLD = 8;

/**
 * Gợi ý "Drag to Look Around" của bản gốc: hiện khi narration của scene đã kết
 * thúc, tự tắt ngay lần đầu người dùng kéo canvas 3D.
 *
 * Component luôn được mount (chỉ ẩn bằng prop `hidden`) để trạng thái "đã kéo"
 * không bị reset khi tạm vào/ra chế độ 3D — nếu unmount thì hint sẽ hiện lại.
 */
export default function LookAroundHint({ hidden }: { hidden: boolean }) {
  const [dragged, setDragged] = useState(false);

  useEffect(() => {
    if (hidden || dragged) return;

    let start: { x: number; y: number } | null = null;

    // Chỉ tính cú kéo trên canvas 3D; kéo thanh seek hay panel không được tính.
    const onPointerDown = (event: PointerEvent) => {
      if (!(event.target instanceof HTMLCanvasElement)) return;
      start = { x: event.clientX, y: event.clientY };
    };

    const onPointerMove = (event: PointerEvent) => {
      if (!start) return;
      if (Math.hypot(event.clientX - start.x, event.clientY - start.y) < DRAG_THRESHOLD) return;
      start = null;
      setDragged(true);
    };

    const onPointerUp = () => {
      start = null;
    };

    // Capture để vẫn nhận được sự kiện khi OrbitControls nuốt/stopPropagation.
    const capture = { capture: true } as const;
    window.addEventListener("pointerdown", onPointerDown, capture);
    window.addEventListener("pointermove", onPointerMove, capture);
    window.addEventListener("pointerup", onPointerUp, capture);
    window.addEventListener("pointercancel", onPointerUp, capture);
    return () => {
      window.removeEventListener("pointerdown", onPointerDown, capture);
      window.removeEventListener("pointermove", onPointerMove, capture);
      window.removeEventListener("pointerup", onPointerUp, capture);
      window.removeEventListener("pointercancel", onPointerUp, capture);
    };
  }, [hidden, dragged]);

  if (hidden || dragged) return null;

  return (
    <div className={styles.interactionHint}>
      <div className={styles.lookaroundHint} id="lookaround-hint">
        <div className={styles.lookaroundHintText}>Drag to Look Around</div>
        <div className={styles.lookaroundHintIcon}>
          <Image src="/images/icon_hand_drag.png" alt="" width={122} height={96} unoptimized />
        </div>
      </div>
    </div>
  );
}
