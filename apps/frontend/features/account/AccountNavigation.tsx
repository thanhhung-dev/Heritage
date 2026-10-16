"use client";

import { useEffect, useId, useRef, useState, type RefObject } from "react";
import Link from "next/link";
import Image from "next/image";
import { Avatar, Button, Dropdown, type MenuProps } from "antd";
import { UserOutlined } from "@ant-design/icons";
import { PUBLIC_ACCOUNT_LINKS } from "@/config/public-account";
import type { AuthMode, PublicAccount } from "./types";
import { usePublicAccount } from "./PublicAccountProvider";
import styles from "./account.module.css";

interface AccountNavigationProps {
  account?: PublicAccount | null;
  onAuthRequest?: (mode: AuthMode) => void;
  onSignOut?: () => void;
  className?: string;
  triggerButtonRef?: RefObject<HTMLButtonElement>;
  onResponsiveClose?: () => void;
}

export function AccountNavigation({
  account: suppliedAccount,
  onAuthRequest,
  onSignOut: suppliedSignOut,
  className,
  triggerButtonRef,
  onResponsiveClose,
}: AccountNavigationProps) {
  const session = usePublicAccount();
  const account = suppliedAccount === undefined ? session.account : suppliedAccount;
  const onSignOut = suppliedSignOut ?? (suppliedAccount === undefined ? session.onSignOut : undefined);
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const internalTriggerRef = useRef<HTMLButtonElement>(null);
  const triggerRef = triggerButtonRef ?? internalTriggerRef;
  const loginRef = useRef<HTMLButtonElement>(null);
  const restoreGuestFocus = useRef(false);
  const previousAccount = useRef(account);

  useEffect(() => {
    if (previousAccount.current !== account) {
      setOpen(false);
      previousAccount.current = account;
    }
    if (!account && restoreGuestFocus.current) {
      loginRef.current?.focus();
      restoreGuestFocus.current = false;
    }
  }, [account]);

  useEffect(() => {
    if (!open) return;

    const desktop = window.matchMedia("(min-width: 768px)");
    const closeOnBreakpointChange = () => {
      setOpen(false);
      if (onResponsiveClose) {
        onResponsiveClose();
      } else {
        triggerRef.current?.focus();
      }
    };

    desktop.addEventListener("change", closeOnBreakpointChange);
    return () => desktop.removeEventListener("change", closeOnBreakpointChange);
  }, [open, onResponsiveClose, triggerRef]);

  if (!account) {
    return (
      <div className={[styles.guest, className].filter(Boolean).join(" ")}>
        <Button ref={loginRef} className={styles.loginButton} onClick={onAuthRequest ? () => onAuthRequest("login") : undefined}>
          Sign In
        </Button>
        <Button type="primary" className={styles.registerButton} onClick={onAuthRequest ? () => onAuthRequest("register") : undefined}>
          Sign Up
        </Button>
      </div>
    );
  }

  const items: MenuProps["items"] = [
    ...PUBLIC_ACCOUNT_LINKS.map((item) => ({
      key: item.key,
      icon: <span aria-hidden="true" className={`${styles.menuIcon} ${styles[item.icon]}`} />,
      disabled: !item.href,
      label: item.href ? <Link href={item.href}>{item.label}</Link> : item.label,
    })),
    { type: "divider" },
    {
      key: "logout",
      icon: <span aria-hidden="true" className={`${styles.menuIcon} ${styles.logout}`} />,
      label: "Logout",
      disabled: !onSignOut,
      onClick: onSignOut ? () => {
        restoreGuestFocus.current = true;
        onSignOut();
      } : undefined,
    },
  ];

  return (
    <div className={styles.authenticated}>
      <button
        type="button"
        className={styles.notificationTrigger}
        disabled
        aria-label="Thông báo (chưa khả dụng)"
        title="Thông báo sẽ được bổ sung khi có chức năng tương ứng"
      >
        <Image src="/figma/account-bell.svg" alt="" aria-hidden="true" width={14} height={14} />
      </button>
      <Dropdown
        open={open}
        onOpenChange={setOpen}
        trigger={["click"]}
        placement="bottomRight"
        align={{ offset: [-7, 2] }}
        autoFocus
        destroyOnHidden
        classNames={{ root: styles.dropdown }}
        menu={{
          id: menuId,
          items,
          onClick: () => {
            setOpen(false);
            triggerRef.current?.focus();
          },
          onKeyDown: (event) => {
            if (event.key === "Escape") {
              event.preventDefault();
              setOpen(false);
              triggerRef.current?.focus();
            }
          },
        }}
        popupRender={(menu) => (
          <div className={styles.dropdownPanel}>
            <div className={styles.accountIdentity}>
              <Avatar size={40} src={account.avatarUrl} icon={<UserOutlined />} className={styles.avatar} />
              <div className={styles.identityText}>
                <p title={account.displayName}>{account.displayName}</p>
                {account.email ? <span title={account.email}>{account.email}</span> : null}
              </div>
            </div>
            {menu}
          </div>
        )}
      >
        <button
          ref={triggerRef}
          type="button"
          className={[styles.avatarTrigger, className].filter(Boolean).join(" ")}
          aria-label={`Tài khoản của ${account.displayName}`}
          aria-haspopup="menu"
          aria-expanded={open}
          aria-controls={open ? menuId : undefined}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setOpen(true);
            }
          }}
        >
          <Image src="/figma/account-user.svg" alt="" aria-hidden="true" width={14} height={14} />
          <span className={styles.accountName} title={account.displayName}>{account.displayName}</span>
        </button>
      </Dropdown>
    </div>
  );
}
