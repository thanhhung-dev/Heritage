import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import logo from "@/access/icons/auth-logo.svg";
import caveImage from "@/access/images/auth-cave.png";
import { ForgotPasswordForm } from "@/features/auth/ForgotPasswordForm";
import styles from "@/features/auth/auth.module.css";

export const metadata: Metadata = { title: "Forgot Password | Heritage" };

export default function ForgotPasswordPage() {
  return (
    <div className={styles.screen}>
      <div className={styles.main}>
        <div className={styles.brandRow}>
          <Link href="/" className={styles.brand}>
            <Image src={logo} alt="Heritage" width={100} height={20} priority />
          </Link>
        </div>
        <div className={styles.center}>
          <div className={styles.card}>
            <h1 id="auth-heading" className={styles.heading}>Khôi phục mật khẩu</h1>
            <p style={{ fontSize: "13.3px", lineHeight: "21px", color: "var(--auth-label)", textAlign: "center", margin: 0 }}>
              Nhập email của bạn để nhận link khôi phục mật khẩu
            </p>
            <div className={styles.cardBody}>
              <ForgotPasswordForm />
              <div className={styles.footer} style={{ minHeight: "auto", paddingTop: "8px" }}>
                <p>
                  Nhớ mật khẩu? <Link href="/sign-in" className={styles.link}>Đăng nhập</Link>
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
      <aside className={styles.aside}>
        <Image src={caveImage} alt="" className={styles.cave} fill priority />
      </aside>
    </div>
  );
}
