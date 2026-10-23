"use client";

import Image from "next/image";
import { useEffect, useState } from "react";
import styles from "../styles.module.css";

const UI_ICONS = "https://tapestry-storage-a0fkf0afgte8hndt.z01.azurefd.net/ui-elements/icons";

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
              {/* Cần gạt ảo: dùng đúng 2 asset gốc của bản thiết kế — đĩa nền
                  và núm chồng lên nhau, núm lệch lên phải (đang được đẩy). */}
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
            <span className={styles.desktopOnly}>Move with WASD keys</span>
            <span className={styles.mobileOnly}>Use the joystick to explore the space</span>
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
