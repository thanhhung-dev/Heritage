"use client";

import { useEffect, useRef } from "react";
import { createTourEngine, type TourEngine } from "./tour-engine";
import styles from "../styles.module.css";

export default function HeritageCanvas({
  onReady,
  onError,
  modelUrl,
  fallbackImageUrl,
}: {
  onReady: (engine: TourEngine | null) => void;
  onError?: (error: string) => void;
  /**
   * GLB của tour. `null`/`undefined` = địa điểm chưa có model 3D trên R2: khi đó
   * không dựng engine mà hiển thị ảnh splash làm nền, để trang scene vẫn dùng
   * được (nội dung scene lấy từ DB, không phụ thuộc model).
   */
  modelUrl?: string | null;
  /** Ảnh nền thay cho canvas khi chưa có model. */
  fallbackImageUrl?: string | null;
}) {
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    // Không có model ⇒ không có engine. Báo `null` để nơi khác biết mà ẩn các
    // điều khiển 3D (xem `isModelReady` trong context).
    if (!modelUrl) {
      onReady(null);
      return;
    }
    onReady(null);
    const handleEngineError = (cause: unknown) => {
      onError?.(
        cause instanceof Error ? cause.message : "Không thể khởi tạo hoặc tải model 3D.",
      );
    };
    try {
      const engine = createTourEngine(
        host,
        modelUrl,
        (message) => {
          if (message === null) onReady(engine);
        },
        handleEngineError,
      );
      return () => engine.dispose();
    } catch (cause) {
      handleEngineError(cause);
    }
  }, [onReady, onError, modelUrl]);

  return (
    <>
      <div className={styles.threeCanvas} ref={hostRef} />
      {!modelUrl && fallbackImageUrl ? (
        <img className={styles.modelFallback} src={fallbackImageUrl} alt="" />
      ) : null}
    </>
  );
}
