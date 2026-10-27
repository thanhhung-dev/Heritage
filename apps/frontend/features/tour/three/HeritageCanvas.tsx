"use client";

import { useEffect, useRef } from "react";
import { createTourEngine, type TourEngine } from "./tour-engine";
import type { ModelProgress } from "./model-loader";
import styles from "../styles.module.css";

export default function HeritageCanvas({
  onReady,
  onError,
  onProgress,
  modelUrl,
  fallbackImageUrl,
}: {
  onReady: (engine: TourEngine | null) => void;
  onError?: (error: string) => void;
  /** Tiến độ tải GLB (0..1) — dùng cho thanh loading ở trang splash. */
  onProgress?: (progress: ModelProgress) => void;
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
  // Giữ callback trong ref để engine không bị dựng lại mỗi lần component render.
  const progressRef = useRef(onProgress);
  progressRef.current = onProgress;

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
        (progress) => progressRef.current?.(progress),
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
