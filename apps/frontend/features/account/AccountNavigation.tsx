"use client";

import { useId, useRef, useState } from "react";
import Link from "next/link";
import { Avatar, Button, Dropdown, type MenuProps } from "antd";
import { DownOutlined, LogoutOutlined, SettingOutlined, UserOutlined } from "@ant-design/icons";
import { PUBLIC_ACCOUNT_LINKS } from "@/config/public-account";
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
        <Button className={styles.loginButton} onClick={onAuthRequest ? () => onAuthRequest("login") : undefined}>
          Đăng nhập
        </Button>
        <Button type="primary" className={styles.registerButton} onClick={onAuthRequest ? () => onAuthRequest("register") : undefined}>
          Đăng ký
        </Button>
      </div>
    );
  }

  const items: MenuProps["items"] = [
    ...PUBLIC_ACCOUNT_LINKS.map((item) => ({
      key: item.key,
      icon: item.key === "profile" ? <UserOutlined /> : <SettingOutlined />,
      disabled: !item.href,
      label: item.href ? <Link href={item.href}>{item.label}</Link> : item.label,
    })),
    { type: "divider" },
    {
      key: "logout",
      icon: <LogoutOutlined />,
      label: "Đăng xuất",
      disabled: !onSignOut,
      onClick: onSignOut,
    },
  ];

  return (
    <Dropdown
      open={open}
      onOpenChange={setOpen}
      trigger={["click"]}
      placement="bottomRight"
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
            <p>{account.displayName}</p>
            {account.email ? <span>{account.email}</span> : null}
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
        <Avatar size={36} src={account.avatarUrl} icon={<UserOutlined />} className={styles.avatar} />
        <DownOutlined aria-hidden="true" className={styles.chevron} />
      </button>
    </Dropdown>
  );
}
