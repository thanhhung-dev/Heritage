"use client";

import { useEffect, useRef, useState } from "react";
import { createTourEngine, type TourEngine } from "./tour-engine";
import styles from "../styles.module.css";

export default function HeritageCanvas({
  landing = false,
  onReady,
}: {
  landing?: boolean;
  onReady: (engine: TourEngine) => void;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<string | null>("Đang tải model 3D Tự Đức (111 MB)…");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const onError = (cause: unknown) => {
      setError(cause instanceof Error ? cause.message : "Không thể khởi tạo hoặc tải model 3D.");
    };
    try {
      const engine = createTourEngine(host, "/tour-assets/tuduc.glb", (message) => {
        setStatus(message);
        if (message === null) onReady(engine);
      }, onError);
      return () => engine.dispose();
    } catch (cause) {
      onError(cause);
    }
  }, [onReady]);

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
