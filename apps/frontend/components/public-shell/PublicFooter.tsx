import Image from "next/image";
import heritageMark from "@/access/icons/heritage-logo-mark.svg";
import Link from "next/link";
import { PUBLIC_FOOTER, type FooterLink } from "@/config/public-footer";
import styles from "./public-footer.module.css";
import { PUBLIC_ROUTE_BY_KEY } from "@/config/public-navigation";

function FooterDestination({ link }: { link: FooterLink }) {
  if (!link.href) {
    return (
      <span className={styles.pendingLink} aria-disabled="true">
        {link.label}
      </span>
    );
  }

  return <Link href={link.href} className={styles.link}>{link.label}</Link>;
}

export function PublicFooter() {
  return (
    <footer className={styles.footer} aria-label="Thông tin Heritage">
      <div className={styles.inner}>
        <div className={styles.identity}>
          <Link href={PUBLIC_ROUTE_BY_KEY.home.href} className={styles.brand} aria-label="Heritage - Trang chủ">
            <span className={styles.mark} aria-hidden="true">
              <Image src={heritageMark} alt="" width={13} height={15} />
            </span>
            <span>HERITAGE</span>
          </Link>
          <p className={styles.description}>{PUBLIC_FOOTER.description}</p>
          <span className={styles.socialMark} aria-hidden="true">𝕏</span>
        </div>
        <div className={styles.groups}>
          {PUBLIC_FOOTER.groups.map((group) => (
            <div key={group.key} className={styles.group}>
              <h2>{group.label}</h2>
              <ul>
                {group.links.map((link) => (
                  <li key={link.key}><FooterDestination link={link} /></li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </footer>
  );
}
