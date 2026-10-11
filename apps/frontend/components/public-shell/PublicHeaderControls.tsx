"use client";

import { useEffect, useId, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Button, Drawer } from "antd";
import { MenuOutlined } from "@ant-design/icons";
import { AccountNavigation } from "@/features/account/AccountNavigation";
import { usePublicAccount } from "@/features/account/PublicAccountProvider";
import type { PublicAccount } from "@/features/account/types";
import { PublicNavigation } from "./PublicNavigation";
import styles from "./public-header-controls.module.css";

interface PublicHeaderControlsProps {
  account?: PublicAccount | null;
  onSignOut?: () => void;
}

export function PublicHeaderControls({ account: suppliedAccount, onSignOut: suppliedSignOut }: PublicHeaderControlsProps) {
  const session = usePublicAccount();
  const account = suppliedAccount === undefined ? session.account : suppliedAccount;
  const onSignOut = suppliedSignOut ?? (suppliedAccount === undefined ? session.onSignOut : undefined);
  const [menuOpen, setMenuOpen] = useState(false);
  const mobileNavigationId = useId();
  const menuTriggerRef = useRef<HTMLButtonElement>(null);
  const menuWasOpened = useRef(false);
  const restoreMobileFocus = useRef(false);
  const pathname = usePathname();

  const signOutFromHeader = onSignOut ? () => {
    restoreMobileFocus.current = window.matchMedia("(max-width: 767px)").matches;
    onSignOut();
  } : undefined;

  useEffect(() => {
    if (!account && restoreMobileFocus.current) {
      menuTriggerRef.current?.focus();
      restoreMobileFocus.current = false;
    }
  }, [account]);

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
        <AccountNavigation account={account} onSignOut={signOutFromHeader} />
      </div>
      <div className={styles.mobile}>
        {account ? <AccountNavigation account={account} onSignOut={signOutFromHeader} /> : null}
        <Button
          ref={menuTriggerRef}
          className={styles.menuTrigger}
          type="text"
          icon={<MenuOutlined />}
          aria-label="Mở menu điều hướng"
          aria-haspopup="dialog"
          aria-expanded={menuOpen}
          aria-controls={menuOpen ? mobileNavigationId : undefined}
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
        <div id={mobileNavigationId}>
          <PublicNavigation className={styles.mobileNavigation} onNavigate={() => setMenuOpen(false)} />
          {!account ? (
            <div className={styles.mobileAccount}>
              <AccountNavigation account={account} />
            </div>
          ) : null}
        </div>
      </Drawer>
    </>
  );
}
