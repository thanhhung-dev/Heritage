"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Button, Drawer } from "antd";
import { MenuOutlined } from "@ant-design/icons";
import { PublicNavigation } from "./PublicNavigation";
import styles from "./public-header-controls.module.css";

export function MobileNavigation() {
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const pathname = usePathname();
  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
      if (event.key !== "Tab") return;
      const dialog = document.querySelector<HTMLElement>("[role=dialog]");
      const items = dialog?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], [tabindex="0"]');
      if (!items?.length) return;
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && (document.activeElement === first || !dialog?.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open]);
  useEffect(() => {
    const media = window.matchMedia("(min-width: 768px)");
    const close = () => { if (media.matches) setOpen(false); };
    media.addEventListener("change", close);
    return () => media.removeEventListener("change", close);
  }, []);
  return <div className={styles.mobile}>
    <Button ref={trigger} className={styles.menuTrigger} type="text" icon={<MenuOutlined />} aria-label="Mở menu điều hướng" aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(true)} />
    <Drawer focusable={{ focusTriggerAfterClose: false }} open={open} onClose={() => setOpen(false)} title="Khám phá Heritage" placement="right" size="min(340px, calc(100vw - 20px))" closable={{ "aria-label": "Đóng menu điều hướng" }} afterOpenChange={(visible) => { if (!visible && window.matchMedia("(max-width: 767px)").matches) trigger.current?.focus(); }} classNames={{ section: styles.drawerContainer, header: styles.drawerHeader, body: styles.drawerBody }}>
      <PublicNavigation className={styles.mobileNavigation} onNavigate={() => setOpen(false)} />
    </Drawer>
  </div>;
}
