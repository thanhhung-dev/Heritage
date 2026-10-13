"use client";

import { useEffect, useRef } from "react";
import { createTourEngine, type TourEngine } from "./tour-engine";
import styles from "../styles.module.css";

export default function HeritageCanvas({
  onReady,
  onError,
  modelUrl = "/tour-assets/tuduc.glb",
}: {
  onReady: (engine: TourEngine | null) => void;
  onError?: (error: string) => void;
  modelUrl?: string;
}) {
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
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

  return <div className={styles.threeCanvas} ref={hostRef} />;
}
