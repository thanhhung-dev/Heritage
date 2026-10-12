"use client";

import type { ExploreMode } from "../three/explore-controller";
import styles from "../styles.module.css";

export default function ExploreControls({ mode, onEnter, onReset, onExit }: {
  mode: ExploreMode | null;
  onEnter: (mode: ExploreMode) => void;
  onReset: () => void;
  onExit: () => void;
}) {
  return (
    <nav className={styles.exploreControls} aria-label="3D exploration">
      {!mode ? <button type="button" onClick={() => onEnter("standard")}>Explore in 3D</button> : <>
        <button type="button" aria-pressed={mode === "standard"} onClick={() => onEnter("standard")}>Standard</button>
        <button type="button" aria-pressed={mode === "free"} onClick={() => onEnter("free")}>Free orbit</button>
        <button type="button" onClick={onReset}>Reset</button>
        <button type="button" onClick={onExit}>Exit</button>
      </>}
    </nav>
  );
}
