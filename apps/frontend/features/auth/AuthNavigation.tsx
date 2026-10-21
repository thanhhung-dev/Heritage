import Link from "next/link";
import { PUBLIC_AUTH_ROUTES } from "@/config/public-auth";
import styles from "./auth-navigation.module.css";

export function AuthNavigation() {
  return (
    <div className={styles.actions} aria-label="Account">
      <Link className={styles.action} href={PUBLIC_AUTH_ROUTES.login}>Sign In</Link>
      <Link className={styles.action} href={PUBLIC_AUTH_ROUTES.register}>Sign Up</Link>
    </div>
  );
}
