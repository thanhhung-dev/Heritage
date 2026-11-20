"use client";

import Link from "next/link";
import { clearAuth } from "../../lib/auth";
import { DesignIcon } from "./DesignIcon";
import { useAdminSession } from "./useAdminSession";
import styles from "./knowledge.module.css";

export function KnowledgeAccount({ collapsed }: { collapsed: boolean }) {
  const { user } = useAdminSession();
  const name = user?.display_name || user?.username || "Administrator";
  const initials = user
    ? name.split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join("").toUpperCase() || name.slice(0, 2).toUpperCase()
    : "?";
  return <>
    <div className={styles.support}>
      {!collapsed && <span className={styles.supportLabel}>Support</span>}
      <Link href="/" aria-label="Back to Chat"><DesignIcon name="library-ArrowLeft" />{!collapsed && "Back to Chat"}</Link>
      <Link href="/sign-in" onClick={() => clearAuth()} aria-label="Account / Sign out"><DesignIcon name="library-CircleUserRound" />{!collapsed && (user ? "Account / Sign out" : "Sign in")}</Link>
    </div>
    <div className={styles.accountFooter} style={collapsed ? { justifyContent: "center", padding: "16px 0" } : undefined}>
      <span className={styles.accountAvatar} aria-hidden="true">{initials}</span>
      {!collapsed && <div className={styles.account}><div className={styles.accountName}>{user ? name : "Not signed in"}</div><span className={styles.accountSub}>Default Workspace</span></div>}
    </div>
  </>;
}
