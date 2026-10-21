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

interface PublicNavigationProps {
  className?: string;
  onNavigate?: () => void;
}

export function PublicNavigation({ className, onNavigate }: PublicNavigationProps = {}) {
  const pathname = usePathname();

  return (
    <nav className={[styles.navigation, className].filter(Boolean).join(" ")} aria-label="Điều hướng chính">
      {PUBLIC_NAVIGATION_ITEMS.map((route) => {
        const isCurrent = isCurrentRoute(pathname, route.href);

        return (
          <Link
            key={route.key}
            href={route.href}
            className={styles.navigationLink}
            aria-current={isCurrent ? "page" : undefined}
            data-active={isCurrent || undefined}
            onClick={onNavigate}
          >
            {route.label}
          </Link>
        );
      })}
    </nav>
  );
}
