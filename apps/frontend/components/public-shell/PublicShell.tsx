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
          <Image
            src="/figma/heritage-logo.png"
            alt=""
            width={20}
            height={20}
            priority
          />
          <span>HERITAGE</span>
        </Link>

        <div className={styles.controls}>
          <form
            className={styles.searchForm}
            action="/explore"
            role="search"
            aria-label="Search heritage collections"
          >
            <button
              className={styles.searchSubmit}
              type="submit"
              aria-label="Search"
            >
              <Image
                src="/figma/search.png"
                alt=""
                width={16}
                height={16}
              />
            </button>
            <input
              className={styles.searchInput}
              type="search"
              name="q"
              aria-label="Search tapestries"
              placeholder="Search Tapestries…"
            />
          </form>
          <PublicNavigation />
        </div>
      </header>

      <main className={styles.main} id="public-content" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
