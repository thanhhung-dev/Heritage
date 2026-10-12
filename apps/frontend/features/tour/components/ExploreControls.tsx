"use client";

import type { ExploreMode } from "../three/explore-controller";
import styles from "../styles.module.css";

export default function ExploreControls({ mode, onEnter, onReset, onExit, initialMode = "standard", onCameraView, zoomed = false }: {
  mode: ExploreMode | null;
  onEnter: (mode: ExploreMode) => void;
  onReset: () => void;
  onExit: () => void;
  initialMode?: ExploreMode;
  onCameraView?: () => void;
  zoomed?: boolean;
}) {
  return (
    <nav className={styles.exploreControls} aria-label="3D exploration">
      {!mode ? <>
        <button type="button" onClick={() => onEnter(initialMode)}>Explore in 3D</button>
        {onCameraView && <button type="button" onClick={onCameraView}>{zoomed ? "Start view" : "Zoom view"}</button>}
      </> : <>
        <button type="button" aria-pressed={mode === "standard"} onClick={() => onEnter("standard")}>Standard</button>
        <button type="button" aria-pressed={mode === "free"} onClick={() => onEnter("free")}>Free orbit</button>
        <button type="button" onClick={onReset}>Reset</button>
        <button type="button" onClick={onExit}>Exit</button>
      </>}
    </nav>
  );
}
