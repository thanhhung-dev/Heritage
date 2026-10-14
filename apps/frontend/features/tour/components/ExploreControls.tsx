"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import type { HeritageInteractive } from "@/types/heritage";
import type { ExploreMode } from "../three/explore-controller";
import styles from "../styles.module.css";

const ICONS = "https://tapestry-storage-a0fkf0afgte8hndt.z01.azurefd.net/ui-elements/icons";
const EXIT_ICON = "https://tapestry-storage-a0fkf0afgte8hndt.z01.azurefd.net/ui-elements/nav_bar_new/playpen_exit_ow.svg";

export default function ExploreControls({ interactive, mode, onEnter, onReset, onExit, initialMode, onSelectHighlight, selectedHighlightId }: {
  interactive: HeritageInteractive | null;
  mode: ExploreMode | null;
  onEnter: (mode: ExploreMode) => void;
  onReset: () => void;
  onExit: () => void;
  initialMode: ExploreMode;
  onSelectHighlight: (id: number) => void;
  selectedHighlightId?: number;
}) {
  const enterRef = useRef<HTMLButtonElement>(null);
  const exitRef = useRef<HTMLButtonElement>(null);
  const [failedThumbnails, setFailedThumbnails] = useState<Record<number, string | null | undefined>>({});
  const focusAfterAction = useRef(false);
  // `.exitCorner` vào bằng opacity 0 → 1 + scale .85 → 1, nên phải mount ở
  // trạng thái chưa active rồi bật ở frame sau, nếu không transition bị bỏ qua.
  const [exitCornerReady, setExitCornerReady] = useState(false);
  useEffect(() => {
    if (!mode) { setExitCornerReady(false); return; }
    let inner = 0;
    const outer = requestAnimationFrame(() => { inner = requestAnimationFrame(() => setExitCornerReady(true)); });
    return () => { cancelAnimationFrame(outer); cancelAnimationFrame(inner); };
  }, [mode]);
  useEffect(() => {
    if (focusAfterAction.current) {
      (mode ? exitRef : enterRef).current?.focus();
      focusAfterAction.current = false;
    }
  }, [mode]);

  if (!interactive) return null;
  if (mode) {
    // Cùng cấu trúc với nút "Dive Deeper" ở góc: một viên kính tròn + nhãn.
    return (
      <div className={`${styles.exitCorner} ${exitCornerReady ? styles.active : ""}`} id="exitCorner">
        <button
          ref={exitRef}
          className={styles["exitCorner-btn"]}
          id="exitCornerBtn"
          type="button"
          aria-label="Exit 3D Mode"
          onClick={() => {
            focusAfterAction.current = true;
            onExit();
          }}
        >
          <Image className={styles["exitCorner-icon"]} src={EXIT_ICON} width={42} height={42} alt="" unoptimized />
        </button>
        <span className={styles["exitCorner-label"]}>Exit 3D Mode</span>
      </div>
    );
  }

  return (
    <div className={`${styles.exploreCorner} ${styles.active} ${initialMode === "free" ? styles["free-explore"] : ""}`} id="exploreCorner">
      <div className={`${styles["exploreCorner-rays"]} ${styles.reveal}`} aria-hidden="true" />
      <Image className={`${styles["exploreCorner-glowSvg"]} ${styles.reveal}`} src="/images/glow_top_right.png" width={700} height={700} alt="" aria-hidden="true" unoptimized />
      <div className={`${styles["exploreCorner-glow"]} ${styles.reveal}`} aria-hidden="true" />
      <div className={styles["exploreCorner-tiltWrap"]} id="exploreCornerTilt">
        <button ref={enterRef} className={`${styles["exploreCorner-btn"]} ${styles.pop}`} id="exploreCornerBtn" type="button"
          aria-label="Dive Deeper — Explore Area in 3D" data-interactive-id={interactive.id}
          onClick={() => { focusAfterAction.current = true; onEnter(initialMode); }}>
          <div className={styles["exploreCorner-iconWrap"]}>
            <Image className={styles["exploreCorner-icon"]} src={`${ICONS}/explore_lens.svg`} width={72} height={72} alt="" unoptimized />
          </div>
          <div className={styles["exploreCorner-shineClip"]} aria-hidden="true"><span className={styles["exploreCorner-shine"]} /></div>
          <div className={styles["exploreCorner-footsteps"]} aria-hidden="true">
            <div className={styles.footstepStrip}>
              {Array.from({ length: 8 }, (_, index) => (
                <Image key={index} className={`${styles.footstep} ${styles[index % 2 === 0 ? "footstep-l" : "footstep-r"]}`}
                  src={`${ICONS}/icon_footstep_${index % 2 === 0 ? "l" : "r"}.svg`} width={26} height={26} alt="" unoptimized />
              ))}
            </div>
          </div>
        </button>
        <span className={`${styles["exploreCorner-label"]} ${styles.show}`} id="dive-deeper-label">Dive Deeper</span>
      </div>
    </div>
  );
}
