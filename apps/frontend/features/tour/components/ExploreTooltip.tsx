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
              {/* Desktop: bàn phím WASD. Mobile: cần gạt ảo (xem `.mobileJoystick`).
                  Chọn bằng CSS để không phải đo breakpoint trong JS. */}
              <Image className={`${styles.exploreTooltipIcon} ${styles.desktopOnly}`} src="/images/icon_wasd.png" alt="" width={128} height={128} unoptimized />
              <Image className={`${styles.exploreTooltipIcon} ${styles["exploreTooltipIcon--glow"]} ${styles.desktopOnly}`} src="/images/icon_wasd_h.png" alt="" width={128} height={128} unoptimized />
              <svg
                className={`${styles.exploreTooltipIcon} ${styles["exploreTooltipIcon--joystick"]} ${styles.mobileOnly}`}
                viewBox="0 0 128 128"
                fill="none"
                aria-hidden="true"
              >
                <circle cx="64" cy="64" r="46" stroke="#fef1d7" strokeWidth="3" opacity="0.45" />
                <circle cx="64" cy="64" r="30" stroke="#fef1d7" strokeWidth="2" opacity="0.2" />
                <circle cx="78" cy="50" r="17" stroke="#fef1d7" strokeWidth="4" fill="rgba(254, 241, 215, 0.14)" />
              </svg>
            </div>
            <span className={styles.desktopOnly}>Move with WASD keys</span>
            <span className={styles.mobileOnly}>Use the joystick to move</span>
          </div>
          {/* Mobile đã có cần gạt ảo để đi, nên gợi ý "drag to look around" và
              icon chuột bị ẩn (xem `.desktopOnly`). */}
          <div className={`${styles.exploreTooltipItem} ${styles.desktopOnly}`}>
            <Image className={`${styles.exploreTooltipIcon} ${styles["exploreTooltipIcon--mouse"]}`} src="/images/icon_mouse.png" alt="" width={128} height={128} unoptimized />
            <span>Drag to look around</span>
          </div>
        </div>
      </div>
    </div>
  );
}
