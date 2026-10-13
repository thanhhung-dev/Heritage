"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import type { HeritageInteractive } from "@/types/heritage";
import type { ExploreMode } from "../three/explore-controller";
import styles from "../styles.module.css";

const ICONS = "https://tapestry-storage-a0fkf0afgte8hndt.z01.azurefd.net/ui-elements/icons";

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
  useEffect(() => {
    if (focusAfterAction.current) {
      (mode ? exitRef : enterRef).current?.focus();
      focusAfterAction.current = false;
    }
  }, [mode]);

  if (!interactive) return null;
  if (mode) return (
    <nav className={styles.exploreControls} aria-label="3D exploration" data-explore-mode={mode}>
      <span className={styles.exploreModeLabel}>{mode === "free" ? "Free orbit" : "Explore in 3D"}</span>
      <div className={styles.exploreActions}>
        <button type="button" onClick={onReset}>Reset view</button>
        <button ref={exitRef} type="button" onClick={() => { focusAfterAction.current = true; onExit(); }}>Exit 3D Mode</button>
      </div>
      {interactive.highlights.length > 0 && (
        <ul className={styles.exploreHighlights} aria-label="Points of interest">
          {[...interactive.highlights].sort((a, b) => a.sort_order - b.sort_order).map((highlight) => (
            <li key={highlight.id}>
              <button type="button" aria-pressed={selectedHighlightId === highlight.id}
                aria-controls={selectedHighlightId === highlight.id ? "hotspot-popup" : undefined}
                onClick={() => onSelectHighlight(highlight.id)}>
                <span className={styles.exploreThumbnail} aria-hidden="true">
                  {highlight.thumb_url && failedThumbnails[highlight.id] !== highlight.thumb_url ? (
                    <Image src={highlight.thumb_url} alt="" fill sizes="64px" unoptimized
                      onError={() => setFailedThumbnails((previous) => ({ ...previous, [highlight.id]: highlight.thumb_url }))} />
                  ) : (
                    <Image src={`${ICONS}/explore_lens.svg`} alt="" width={28} height={28} unoptimized />
                  )}
                </span>
                <span className={styles.explorePointTitle}>{highlight.popup_title ?? "Highlight"}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </nav>
  );

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
