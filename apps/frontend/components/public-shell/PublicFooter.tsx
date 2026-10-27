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

  const isExternal = link.href.startsWith("http");

  return (
    <Link
      href={link.href}
      className={styles.link}
      target={isExternal ? "_blank" : undefined}
      rel={isExternal ? "noopener noreferrer" : undefined}
    >
      {link.label}
    </Link>
  );
}

/**
 * 4 Icon mạng xã hội SVG chuẩn (X, LinkedIn, TikTok, Instagram)
 * kích thước thu gọn 18px, màu rgba(255, 255, 255, 0.55), hover chuyển #FFFFFF
 */
function SocialIcons() {
  return (
    <div className={styles.socialRow} aria-label="Social media links">
      {/* X (Twitter) */}
      <a
        href="https://x.com"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Follow us on X"
        className={styles.socialIconLink}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
        </svg>
      </a>

      {/* LinkedIn */}
      <a
        href="https://linkedin.com"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Connect on LinkedIn"
        className={styles.socialIconLink}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 8.76c-.97 0-1.75-.79-1.75-1.76s.78-1.75 1.75-1.75a1.76 1.76 0 0 1 1.76 1.75c0 .97-.79 1.76-1.76 1.76m1.39 9.74v-8.37H5.07v8.37h2.78Z" />
        </svg>
      </a>

      {/* TikTok */}
      <a
        href="https://tiktok.com"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Watch on TikTok"
        className={styles.socialIconLink}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.97-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.24 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z" />
        </svg>
      </a>

      {/* Instagram */}
      <a
        href="https://instagram.com"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Follow us on Instagram"
        className={styles.socialIconLink}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zM12 16a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z" />
        </svg>
      </a>
    </div>
  );
}

export function PublicFooter() {
  return (
    <footer className={styles.footer} aria-label="Thông tin Heritage">
      <div className={styles.inner}>
        <div className={styles.topRow}>
          {/* Cột trái: Logo, slogan thu nhỏ, hàng icon mạng xã hội 18px */}
          <div className={styles.identity}>
            <Link
              href={PUBLIC_ROUTE_BY_KEY.home.href}
              className={styles.brand}
              aria-label="Heritage - Trang chủ"
            >
              <span className={styles.mark} aria-hidden="true">
                <Image src={heritageMark} alt="" width={13} height={15} />
              </span>
              <span>HERITAGE</span>
            </Link>
            <p className={styles.slogan}>{PUBLIC_FOOTER.description}</p>
            <SocialIcons />
          </div>

          {/* Cột phải: 2 nhóm liên kết About HERITAGE & Socials */}
          <div className={styles.groups}>
            {PUBLIC_FOOTER.groups.map((group) => (
              <div key={group.key} className={styles.group}>
                <h3 className={styles.groupTitle}>{group.label}</h3>
                <ul className={styles.groupList}>
                  {group.links.map((link) => (
                    <li key={link.key}>
                      <FooterDestination link={link} />
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Đáy Footer (Bottom Bar): Dòng copyright căn mờ ở giữa */}
        <div className={styles.bottomBar}>
          <p className={styles.copyright}>
            © 2026 HERITAGE. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}

export default PublicFooter;
