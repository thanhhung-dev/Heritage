"use client";

import { useEffect, useRef, useState } from "react";
import { createTourEngine, type TourEngine } from "./tour-engine";
import styles from "../styles.module.css";

export default function HeritageCanvas({
  landing = false,
  onReady,
  modelUrl = "/tour-assets/tuduc.glb",
}: {
  landing?: boolean;
  onReady: (engine: TourEngine | null) => void;
  modelUrl?: string;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<string | null>("Đang tải model 3D…");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    onReady(null);
    setStatus("Đang tải model 3D…");
    setError(null);
    const onError = (cause: unknown) => {
      setError(cause instanceof Error ? cause.message : "Không thể khởi tạo hoặc tải model 3D.");
    };
    try {
      const engine = createTourEngine(host, modelUrl, (message) => {
        setStatus(message);
        if (message === null) onReady(engine);
      }, onError);
      return () => engine.dispose();
    } catch (cause) {
      onError(cause);
    }
  }, [onReady, modelUrl]);

  return (
    <>
      <div className={styles.threeCanvas} ref={hostRef} />
      {(error || status) && (
        <div
          className={`${styles.threeStatus} ${landing ? styles.threeStatusLanding : ""}`}
          role={error ? "alert" : "status"}
        >
          {error || status}
        </div>
      )}
    </>
  );
}
