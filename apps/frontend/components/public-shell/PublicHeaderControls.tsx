"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Button, Drawer } from "antd";
import { MenuOutlined } from "@ant-design/icons";
import { AccountNavigation } from "@/features/account/AccountNavigation";
import type { PublicAccount } from "@/features/account/types";
import { PublicNavigation } from "./PublicNavigation";
import styles from "./public-header-controls.module.css";

interface PublicHeaderControlsProps {
  account?: PublicAccount | null;
}

export function PublicHeaderControls({ account }: PublicHeaderControlsProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuTriggerRef = useRef<HTMLButtonElement>(null);
  const menuWasOpened = useRef(false);
  const pathname = usePathname();

  useEffect(() => { setMenuOpen(false); }, [pathname]);

  useEffect(() => {
    if (menuOpen) {
      menuWasOpened.current = true;
    } else if (menuWasOpened.current && window.matchMedia("(max-width: 767px)").matches) {
      menuTriggerRef.current?.focus();
    }
  }, [menuOpen]);

  useEffect(() => {
    const desktop = window.matchMedia("(min-width: 768px)");
    const closeOnDesktop = () => { if (desktop.matches) setMenuOpen(false); };
    desktop.addEventListener("change", closeOnDesktop);
    return () => desktop.removeEventListener("change", closeOnDesktop);
  }, []);

  return (
    <>
      <div className={styles.desktop}>
        <PublicNavigation />
        <AccountNavigation account={account} />
      </div>
      <div className={styles.mobile}>
        {account ? <AccountNavigation account={account} /> : null}
        <Button
          ref={menuTriggerRef}
          className={styles.menuTrigger}
          type="text"
          icon={<MenuOutlined />}
          aria-label="Mở menu điều hướng"
          aria-haspopup="dialog"
          aria-expanded={menuOpen}
          aria-controls={menuOpen ? "public-mobile-navigation" : undefined}
          onClick={() => setMenuOpen(true)}
        />
      </div>
      <Drawer
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        placement="right"
        size="min(340px, calc(100vw - 20px))"
        title="Khám phá Heritage"
        closable={{ "aria-label": "Đóng menu điều hướng" }}
        destroyOnHidden
        focusable={{ focusTriggerAfterClose: false }}
        classNames={{ root: styles.drawerRoot, section: styles.drawerContainer, header: styles.drawerHeader, body: styles.drawerBody }}
        afterOpenChange={(open) => {
          if (!open && window.matchMedia("(max-width: 767px)").matches) {
            menuTriggerRef.current?.focus();
          }
        }}
      >
        <div id="public-mobile-navigation">
          <PublicNavigation className={styles.mobileNavigation} onNavigate={() => setMenuOpen(false)} />
          {!account ? (
            <div className={styles.mobileAccount}>
              <AccountNavigation />
            </div>
          ) : null}
        </div>
      </Drawer>
    </>
  );
}
