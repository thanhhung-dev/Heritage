"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import styles from "../styles.module.css";

const ICONS = "https://tapestry-storage-a0fkf0afgte8hndt.z01.azurefd.net/ui-elements/icons";
const NUDGE_INTERVAL_MS = 10_000;
const MOBILE_BREAKPOINT = 769;
const MOVE_KEYS = new Set(["w", "a", "s", "d"]);

export default function ExploreInfoPanel({ title, description }: {
  title: string | null;
  description: string | null;
}) {
  const panelRef = useRef<HTMLElement>(null);
  const [nudge, setNudge] = useState(false);
  const [collapsed, setCollapsed] = useState(
    () => typeof window !== "undefined" && window.innerWidth < MOBILE_BREAKPOINT,
  );

  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      if (!panelRef.current?.contains(event.target as Node)) setCollapsed(true);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (MOVE_KEYS.has(event.key.toLowerCase())) setCollapsed(true);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  useEffect(() => {
    if (!collapsed) { setNudge(false); return; }
    const id = window.setInterval(() => {
      setNudge(true);
      window.setTimeout(() => setNudge(false), 600);
    }, NUDGE_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, [collapsed]);

  if (!title && !description) return null;

  return (
    <aside
      id="exploreInfoPanel"
      ref={panelRef}
      className={`${styles.hotspotPopup} ${styles.playpenInfoParent} ${styles.exploreInfoPanel} ${collapsed ? `${styles.collapsed}${nudge ? ` ${styles.nudge}` : ""}` : ""}`}
      data-collapsed={collapsed}
      aria-labelledby="exploreInfoTitle"
    >
      <button
        id="playpenInfoCollapse"
        className={styles.infoCollapse}
        type="button"
        aria-label={collapsed ? "Expand info panel" : "Collapse info panel"}
        aria-expanded={!collapsed}
        aria-controls="exploreInfoInner"
        onClick={() => setCollapsed((value) => !value)}
      >
        <Image className={`${styles.infoCollapseIcon} ${styles.collapseIn}`} src={`${ICONS}/icon_collapse_in.svg`} alt="" width={40} height={40} unoptimized />
        <Image className={`${styles.infoCollapseIcon} ${styles.collapseOut}`} src={`${ICONS}/icon_collapse_out.svg`} alt="" width={40} height={40} unoptimized />
      </button>
      {title && (
        <h2 id="exploreInfoTitle" className={styles["playpenInfo-Title"]} hidden={collapsed}>{title}</h2>
      )}
      {description && (
        <div id="exploreInfoInner" className={styles.infoInner} hidden={collapsed}>
          <p id="exploreInfoDesc" className={styles["playpenInfo-Desc"]}>{description}</p>
        </div>
      )}
    </aside>
  );
}
