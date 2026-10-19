import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import { Suspense } from "react";
import logo from "@/access/icons/auth-logo.svg";
import caveImage from "@/access/images/auth-cave.png";
import { ResetPasswordForm } from "@/features/auth/ResetPasswordForm";
import styles from "@/features/auth/auth.module.css";

export const metadata: Metadata = { title: "Reset Password | Heritage" };

function ResetPasswordContent() {
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
            <h1 id="auth-heading" className={styles.heading}>Đặt lại mật khẩu</h1>
            <p style={{ fontSize: "13.3px", lineHeight: "21px", color: "var(--auth-label)", textAlign: "center", margin: 0 }}>
              Nhập mật khẩu mới cho tài khoản của bạn
            </p>
            <div className={styles.cardBody}>
              <ResetPasswordForm />
              <div className={styles.footer} style={{ minHeight: "auto", paddingTop: "8px" }}>
                <p>
                  <Link href="/sign-in" className={styles.link}>Quay lại đăng nhập</Link>
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

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <ResetPasswordContent />
    </Suspense>
  );
}
