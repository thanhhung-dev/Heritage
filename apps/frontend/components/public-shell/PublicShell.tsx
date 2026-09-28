import Link from "next/link";
import Image from "next/image";
import type { ReactNode } from "react";
import { PublicNavigation } from "./PublicNavigation";
import styles from "./public-shell.module.css";

interface PublicShellProps {
  children: ReactNode;
}

export function PublicShell({ children }: PublicShellProps) {
  return (
    <div className={styles.shell}>
      <a className={styles.skipLink} href="#public-content">
        Bỏ qua điều hướng
      </a>

      <header className={styles.header}>
        <Link
          className={styles.brand}
          href="/"
          aria-label="Heritage - Trang chủ"
        >
          <span className={styles.logoMark} aria-hidden="true">
            <span className={styles.logoMarkMask}>
              <Image
                className={styles.logoMarkFill}
                src="/figma/heritage-logo-mark.svg"
                alt=""
                width={24}
                height={24}
                priority
              />
            </span>
          </span>
          <span>HERITAGE</span>
        </Link>

        <div className={styles.controls}>
          <div
            className={styles.searchField}
            role="search"
            aria-label="Search heritage collections"
          >
            <Image src="/figma/search.svg" alt="" width={16} height={16} />
            <input
              className={styles.searchInput}
              type="search"
              aria-label="Search Tapestries"
              placeholder="Search Tapestries…"
            />
          </div>
          <PublicNavigation />
        </div>
      </header>

      <main className={styles.main} id="public-content" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
