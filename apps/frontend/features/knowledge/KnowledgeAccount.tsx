"use client";

import Link from "next/link";
import { Avatar } from "antd";
import { clearAuth } from "../../lib/auth";
import { DesignIcon } from "./DesignIcon";
import { useAdminSession } from "./useAdminSession";
import styles from "./knowledge.module.css";

export function KnowledgeAccount({ collapsed }: { collapsed: boolean }) {
  const { user } = useAdminSession();
  const name = user?.display_name || user?.username || "Administrator";
  return <>
    <div className={styles.support}>
      {!collapsed && <span className={styles.muted}>Support</span>}
      <Link href="/" aria-label="Back to Chat"><DesignIcon name="library-ArrowLeft" />{!collapsed && "Back to Chat"}</Link>
      <Link href="/sign-in" onClick={() => clearAuth()} aria-label="Sign out"><DesignIcon name="library-CircleUserRound" />{!collapsed && (user ? "Sign out" : "Sign in")}</Link>
    </div>
    <div className={styles.accountFooter} style={collapsed ? { justifyContent: "center", padding: "16px 0" } : undefined}>
      <Avatar shape="square" size={32} style={{ background: "#ebe9e0", color: "#615f57", fontSize: 12 }}>{user ? name.slice(0, 2).toUpperCase() : "?"}</Avatar>
      {!collapsed && <div className={styles.account}><div className={styles.accountName}>{user ? name : "Not signed in"}</div><span className={styles.muted}>Heritage workspace</span></div>}
    </div>
  </>;
}
