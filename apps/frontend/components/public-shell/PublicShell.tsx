import Link from "next/link";
import Image from "next/image";
import searchIcon from "@/access/icons/search.svg";
import type { ReactNode } from "react";
import { PublicHeaderControls } from "./PublicHeaderControls";
import { PublicFooter } from "./PublicFooter";
import { PublicFooterSlot } from "./PublicFooterSlot";
import type { PublicAccount } from "@/features/account/types";
import styles from "./public-shell.module.css";
import { LogoText } from "../LogoText";
import { PUBLIC_ROUTE_BY_KEY } from "@/config/public-navigation";

interface PublicShellProps {
  children: ReactNode;
  account?: PublicAccount | null;
}

export function PublicShell({ children, account }: PublicShellProps) {
  return (
    <div className={styles.shell}>
      <a className={styles.skipLink} href="#public-content">
        Bỏ qua điều hướng
      </a>

      <header className={styles.header}>
        <Link
          className={styles.brand}
          href={PUBLIC_ROUTE_BY_KEY.home.href}
          aria-label="Heritage - Trang chủ"
        >
          <LogoText size={120}/>
        </Link>

        <div className={styles.controls}>
          <div
            className={styles.searchField}
            role="search"
            aria-label="Search heritage collections"
          >
            <Image src={searchIcon} alt="" width={16} height={16} />
            <input
              className={styles.searchInput}
              type="search"
              name="heritage-search"
              autoComplete="off"
              aria-label="Search Heritages…"
              placeholder="Search Heritages…"
            />
          </div>
          <PublicHeaderControls account={account} />
        </div>
      </header>

      <main className={styles.main} id="public-content" tabIndex={-1}>
        {children}
      </main>
      <PublicFooterSlot><PublicFooter /></PublicFooterSlot>
    </div>
  );
}
