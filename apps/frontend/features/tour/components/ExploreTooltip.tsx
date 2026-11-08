"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import styles from "../styles.module.css";

const UI_ICONS = "https://tapestry-storage-a0fkf0afgte8hndt.z01.azurefd.net/ui-elements/icons";
const TUTORIAL_ASSETS = "https://tapestry-storage-a0fkf0afgte8hndt.z01.azurefd.net/ui-elements/tutorial";

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

/**
 * Tooltip hướng dẫn "Hover to Rotate" (#rotateTooltip) khi vào chế độ khám phá 3D
 * (`standard` hoặc `free`). Tự ẩn sau thao tác con trỏ đầu tiên.
 */
export function RotateTooltip() {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const dismiss = () => setVisible(false);
    document.addEventListener("pointerdown", dismiss, { once: true });
    return () => document.removeEventListener("pointerdown", dismiss);
  }, []);

  if (!visible) return null;

  return (
    <div className={styles.centerUI} aria-hidden="true">
      <div id="rotateTooltip" className={`${styles.rotateTooltip} ${styles.visible}`}>
        <div className={styles.rotateTooltipText}>Hover to Rotate</div>
        <div className={styles.rotateTooltipGif}>
          <Image
            className={styles.rotateToolTip}
            src={`${TUTORIAL_ASSETS}/rotate_tooltip.gif`}
            alt="Rotate Tool Tip: prompt to hover and rotate"
            width={120}
            height={120}
            unoptimized
          />
        </div>
      </div>
    </div>
  );
}
