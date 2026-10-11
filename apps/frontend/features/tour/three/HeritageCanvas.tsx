"use client";

import { useEffect, useRef, useState } from "react";
import { createTourEngine } from "./tour-engine";
import styles from "../styles.module.css";

export default function HeritageCanvas() {
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
      return createTourEngine(host, "/tour-assets/tuduc.glb", setStatus, onError);
    } catch (cause) {
      onError(cause);
    }
  }, []);

  return (
    <>
      <div className={styles.threeCanvas} ref={hostRef} />
      {(error || status) && (
        <div className={styles.threeStatus} role={error ? "alert" : "status"}>
          {error || status}
        </div>
      )}
    </>
  );
}
