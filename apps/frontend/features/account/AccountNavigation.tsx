"use client";

import { useId, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { Avatar, Button, Dropdown, type MenuProps } from "antd";
import { UserOutlined } from "@ant-design/icons";
import { PUBLIC_ACCOUNT_LINKS } from "@/config/public-account";
import { PUBLIC_AUTH_ROUTES } from "@/config/public-auth";
import type { AuthMode, PublicAccount } from "./types";
import styles from "./account.module.css";

interface AccountNavigationProps {
  account?: PublicAccount | null;
  onAuthRequest?: (mode: AuthMode) => void;
  onSignOut?: () => void;
  className?: string;
}

export function AccountNavigation({
  account,
  onAuthRequest,
  onSignOut,
  className,
}: AccountNavigationProps) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const triggerRef = useRef<HTMLButtonElement>(null);

  if (!account) {
    return (
      <div className={[styles.guest, className].filter(Boolean).join(" ")}>
        <Button className={styles.loginButton} href={onAuthRequest ? undefined : PUBLIC_AUTH_ROUTES.login} onClick={onAuthRequest ? () => onAuthRequest("login") : undefined}>
          Sign In
        </Button>
        <Button className={styles.registerButton} href={onAuthRequest ? undefined : PUBLIC_AUTH_ROUTES.register} onClick={onAuthRequest ? () => onAuthRequest("register") : undefined}>
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
      onClick: onSignOut,
    },
  ];

  return (
    <div className={styles.authenticated}>
      <button type="button" className={styles.notificationTrigger} aria-label="Notifications" disabled title="Notifications are not available yet">
        <Image src="/figma/account-bell.svg" width={14} height={14} alt="" aria-hidden="true" />
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
              <Avatar size={27} src={account.avatarUrl} icon={<UserOutlined />} className={styles.avatar} />
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
          <Image src="/figma/account-user.svg" width={14} height={14} alt="" aria-hidden="true" />
        </button>
      </Dropdown>
    </div>
  );
}
