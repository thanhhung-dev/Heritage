"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PUBLIC_NAVIGATION_ITEMS } from "@/config/public-navigation";
import styles from "./public-shell.module.css";

function isCurrentRoute(pathname: string, href: string) {
  return href === "/"
    ? pathname === href
    : pathname === href || pathname.startsWith(`${href}/`);
}

export function PublicNavigation() {
  const pathname = usePathname();

  return (
    <nav className={styles.navigation} aria-label="Điều hướng chính">
      {PUBLIC_NAVIGATION_ITEMS.map((route) => {
        const isCurrent = isCurrentRoute(pathname, route.href);

        return (
          <Link
            key={route.key}
            href={route.href}
            className={styles.navigationLink}
            aria-current={isCurrent ? "page" : undefined}
            data-active={isCurrent || undefined}
          >
            {route.label}
          </Link>
        );
      })}
    </nav>
  );
}
