"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import styles from "../styles.module.css";
export default function ExploreTooltip() {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const dismiss = () => setVisible(false);
    document.addEventListener("pointerdown", dismiss, { once: true });
    return () => document.removeEventListener("pointerdown", dismiss);
  }, []);

  return (
    <div className={styles.centerUI} aria-hidden="true">
      <div id="exploreTooltip" className={`${styles.exploreTooltip} ${visible ? styles.visible : ""}`}>
        <div className={styles.exploreTooltipIcons}>
          <div className={styles.exploreTooltipItem}>
            <div className={styles["exploreTooltipIcon-wrap"]}>
              <Image className={styles.exploreTooltipIcon} src="/images/icon_wasd.png" alt="" width={128} height={128} unoptimized />
              <Image className={`${styles.exploreTooltipIcon} ${styles["exploreTooltipIcon--glow"]}`} src="/images/icon_wasd_h.png" alt="" width={128} height={128} unoptimized />
            </div>
            <span>Move with WASD keys</span>
          </div>
          <div className={styles.exploreTooltipItem}>
            <Image className={`${styles.exploreTooltipIcon} ${styles["exploreTooltipIcon--mouse"]}`} src="/images/icon_mouse.png" alt="" width={128} height={128} unoptimized />
            <span>Drag to look around</span>
          </div>
        </div>
      </div>
    </div>
  );
}
