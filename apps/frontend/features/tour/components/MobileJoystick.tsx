"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import styles from "../styles.module.css";

/**
 * Cần gạt ảo cho chế độ đi bộ trên mobile.
 *
 * Bàn phím WASD không tồn tại trên điện thoại, và cử chỉ kéo trên canvas chỉ
 * đổi hướng nhìn chứ không đi được quãng dài. Cần gạt này đẩy thẳng vào
 * `WalkInput` của engine (`setWalkStick` / `releaseWalkStick`).
 *
 * Quy ước trục giống `createWalkInput`: y dương là kéo XUỐNG (lùi), x dương là
 * quay camera sang phải. Cả hai đã chuẩn hoá `[-1, 1]` trước khi đưa xuống
 * engine — engine mới là nơi áp vùng chết `INPUT_DEAD_ZONE`.
 */

/** Đường kính thumb (px) — phải khớp `.mobileJoystickThumb` trong CSS. */
const THUMB_SIZE = 52;
/** Đường kính đế (px) — phải khớp `.mobileJoystick`. */
const BASE_SIZE = 130;
/** Thumb chạy được bao xa tính từ tâm (px). */
const MAX_TRAVEL = (BASE_SIZE - THUMB_SIZE) / 2;

export default function MobileJoystick({
  onChange,
  onRelease,
}: {
  onChange: (x: number, y: number) => void;
  onRelease: () => void;
}) {
  const baseRef = useRef<HTMLDivElement>(null);
  const pointerId = useRef<number | null>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  // `player.releaseWalkStick` là hàm mới ở mỗi lần render của HeritageViewer.
  // Giữ nó trong ref để `release` có identity ỔN ĐỊNH — nếu không, mỗi lần
  // `setOffset` gây re-render là effect dọn dẹp chạy lại và nhả cần gạt giữa
  // lúc đang kéo.
  const onReleaseRef = useRef(onRelease);
  onReleaseRef.current = onRelease;

  const release = useCallback(() => {
    pointerId.current = null;
    setOffset({ x: 0, y: 0 });
    onReleaseRef.current();
  }, []);

  // Rời chế độ đi bộ khi ngón tay vẫn đang giữ: phải nhả input, không thì
  // camera trôi mãi sau khi component bị gỡ.
  useEffect(() => release, [release]);

  const track = (clientX: number, clientY: number) => {
    const rect = baseRef.current?.getBoundingClientRect();
    if (!rect) return;
    const dx = clientX - (rect.left + rect.width / 2);
    const dy = clientY - (rect.top + rect.height / 2);
    const length = Math.hypot(dx, dy);
    // Kéo quá vành thì thumb bám vành, hướng giữ nguyên.
    const scale = length > MAX_TRAVEL ? MAX_TRAVEL / length : 1;
    const x = dx * scale;
    const y = dy * scale;
    setOffset({ x, y });
    onChange(x / MAX_TRAVEL, y / MAX_TRAVEL);
  };

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (pointerId.current !== null) return;
    pointerId.current = event.pointerId;
    // Giữ được cần gạt cả khi ngón tay trượt ra ngoài đế.
    event.currentTarget.setPointerCapture(event.pointerId);
    track(event.clientX, event.clientY);
  };

  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.pointerId !== pointerId.current) return;
    track(event.clientX, event.clientY);
  };

  const onPointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
    if (event.pointerId !== pointerId.current) return;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    release();
  };

  return (
    <div
      id="mobileJoystickBase"
      ref={baseRef}
      className={styles.mobileJoystick}
      aria-hidden="true"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      <div
        id="mobileJoystickThumb"
        className={styles.mobileJoystickThumb}
        style={{ transform: `translate(${offset.x}px, ${offset.y}px)` }}
      />
    </div>
  );
}
