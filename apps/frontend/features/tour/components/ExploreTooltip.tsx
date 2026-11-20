"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import styles from "@/features/tour/styles.module.css";

const UI_ICONS = "https://tapestry-storage-a0fkf0afgte8hndt.z01.azurefd.net/ui-elements/icons";

export default function ExploreTooltip() {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const dismiss = () => setVisible(false);
    document.addEventListener("pointerdown", dismiss, { once: true });
    return () => document.removeEventListener("pointerdown", dismiss);
  }, []);

  return (
    <>
      <div className={styles.centerUI} aria-hidden="true">
        <div id="exploreTooltip" className={`${styles.exploreTooltip} ${visible ? styles.visible : ""}`}>
          <div className={styles.exploreTooltipIcons}>
            <div className={`${styles.exploreTooltipItem} ${styles.desktopOnly}`}>
              <div className={styles["exploreTooltipIcon-wrap"]}>
                <Image className={styles.exploreTooltipIcon} src="/images/icon_wasd.png" alt="WASD keys" width={128} height={128} unoptimized />
                <Image className={`${styles.exploreTooltipIcon} ${styles["exploreTooltipIcon--glow"]}`} src="/images/icon_wasd_h.png" alt="" width={128} height={128} unoptimized />
              </div>
              <span>Move with WASD keys</span>
            </div>
            <div className={`${styles.exploreTooltipItem} ${styles.desktopOnly}`}>
              <Image className={`${styles.exploreTooltipIcon} ${styles["exploreTooltipIcon--mouse"]}`} src="/images/icon_mouse.png" alt="Mouse drag" width={128} height={128} unoptimized />
              <span>Drag to look around</span>
            </div>
          </div>
        </div>
      </div>

      <div className={styles.centerUI} aria-hidden="true">
        <div
          id="exploreMobileTooltip"
          className={`${styles.exploreMobileTooltip} ${visible ? styles.visible : ""}`}
        >
          <div className={styles["joystickTooltipIcon-wrap"]}>
            <Image
              className={styles.joystickTooltipBase}
              src={`${UI_ICONS}/icon_joystick_base.svg`}
              alt=""
              width={64}
              height={64}
              unoptimized
            />
            <Image
              className={styles.joystickTooltipTop}
              src={`${UI_ICONS}/icon_joystick_top.svg`}
              alt=""
              width={32}
              height={32}
              unoptimized
            />
          </div>
          <div className={styles.joystickTooltipText}>Use the joystick to explore the space</div>
        </div>
      </div>
    </>
  );
}
