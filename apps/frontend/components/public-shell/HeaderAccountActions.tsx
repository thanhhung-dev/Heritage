"use client";

import {
  useEffect,
  useId,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import {
  LogoutOutlined,
  QuestionCircleOutlined,
  SettingOutlined,
  TranslationOutlined,
} from "@ant-design/icons";
import bellIcon from "@/access/icons/account-bell.svg";
import { UserAvatar } from "@/features/account/UserAvatar";
import { PUBLIC_AUTH_ROUTES } from "@/config/public-auth";
import { AUTH_CHANGE_EVENT, clearAuth, getUser, isAuthenticated } from "@/lib/auth";
import styles from "./public-shell.module.css";

function subscribeToSession(onStoreChange: () => void) {
  window.addEventListener(AUTH_CHANGE_EVENT, onStoreChange);
  window.addEventListener("storage", onStoreChange);

  return () => {
    window.removeEventListener(AUTH_CHANGE_EVENT, onStoreChange);
    window.removeEventListener("storage", onStoreChange);
  };
}

function getSessionSnapshot() {
  return isAuthenticated();
}

function getServerSessionSnapshot() {
  return false;
}

export function HeaderAccountActions() {
  const authenticated = useSyncExternalStore(
    subscribeToSession,
    getSessionSnapshot,
    getServerSessionSnapshot,
  );
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const menuWrapperRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  // Close the menu when navigating or when the session ends.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!authenticated) {
      setOpen(false);
    }
  }, [authenticated]);

  // Click/tap outside + Escape close handling.
  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (event: MouseEvent | TouchEvent) => {
      if (!menuWrapperRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("touchstart", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("touchstart", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  if (!authenticated) {
    return (
      <Link className={styles.authAction} href={PUBLIC_AUTH_ROUTES.login}>
        Sign In
      </Link>
    );
  }

  // Safe to read on the client: the server snapshot always reports a guest.
  const user = getUser();
  const displayName =
    user?.display_name?.trim() || user?.username?.trim() || "Heritage Explorer";
  const email = user?.email || "";

  const handleLogout = () => {
    setOpen(false);
    clearAuth();
    router.push("/");
  };

  return (
    <div className={styles.authIcons}>
      <button
        type="button"
        className={styles.iconButton}
        aria-label="Notifications"
        title="Notifications"
        disabled
      >
        <Image src={bellIcon} alt="" aria-hidden="true" width={16} height={16} />
      </button>

      <div className={styles.accountMenuWrap} ref={menuWrapperRef}>
        <button
          ref={triggerRef}
          type="button"
          className={styles.avatarTrigger}
          onClick={() => setOpen((current) => !current)}
          aria-label="Open account menu"
          aria-haspopup="menu"
          aria-expanded={open}
          aria-controls={open ? menuId : undefined}
        >
          <UserAvatar
            src={user?.avatar_url}
            name={displayName}
            size={32}
            alt=""
          />
        </button>

        {open ? (
          <div
            id={menuId}
            className={styles.accountMenu}
            role="menu"
            aria-label="Account menu"
          >
            <div className={styles.accountSummary}>
              <UserAvatar
                src={user?.avatar_url}
                name={displayName}
                size={44}
                alt=""
              />
              <div className={styles.accountIdentity}>
                <span className={styles.accountName}>{displayName}</span>
                {email ? <span className={styles.accountEmail}>{email}</span> : null}
              </div>
            </div>

            <div className={styles.accountMenuDivider} role="separator" />

            <Link
              href="/profile"
              role="menuitem"
              className={styles.accountMenuItem}
              onClick={() => setOpen(false)}
            >
              <SettingOutlined
                className={styles.accountMenuIcon}
                aria-hidden="true"
              />
              <span>Account Profile</span>
            </Link>

            <Link
              href="/faq"
              role="menuitem"
              className={styles.accountMenuItem}
              onClick={() => setOpen(false)}
            >
              <QuestionCircleOutlined
                className={styles.accountMenuIcon}
                aria-hidden="true"
              />
              <span>Help Center</span>
            </Link>

            <button
              type="button"
              role="menuitem"
              className={styles.accountMenuItem}
              disabled
              aria-disabled="true"
              title="Language settings are coming soon"
            >
              <TranslationOutlined
                className={styles.accountMenuIcon}
                aria-hidden="true"
              />
              <span>Language</span>
            </button>

            <div className={styles.accountMenuDivider} role="separator" />

            <button
              type="button"
              role="menuitem"
              className={`${styles.accountMenuItem} ${styles.accountMenuLogout}`}
              onClick={handleLogout}
            >
              <LogoutOutlined
                className={styles.accountMenuIcon}
                aria-hidden="true"
              />
              <span>Logout</span>
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
