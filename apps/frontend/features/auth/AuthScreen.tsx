import Image from "next/image";
import Link from "next/link";
import { PUBLIC_AUTH_POLICIES, PUBLIC_AUTH_ROUTES } from "@/config/public-auth";
import { PUBLIC_ROUTE_BY_KEY } from "@/config/public-navigation";
import type { AuthMode } from "@/features/account/types";
import { SignInForm } from "./SignInForm";
import { SocialAuthButtons } from "./SocialAuthButtons";
import styles from "./auth.module.css";

export function AuthScreen({ mode }: { mode: AuthMode }) {
  const signIn = mode === "login";

  return (
    <main className={styles.screen}>
      <div className={styles.main}>
        <header className={styles.brandRow}>
          <Link href={PUBLIC_ROUTE_BY_KEY.home.href} aria-label="Heritage home" className={styles.brand}>
            <Image src="/figma/auth-logo.svg" alt="Heritage" width={103} height={20} priority />
          </Link>
        </header>
        <div className={styles.center}>
          <section className={styles.card} aria-labelledby="auth-heading">
            <h1 id="auth-heading" className={styles.heading}>{signIn ? "Log in to your account" : "Create a Heritage account"}</h1>
            <div className={styles.cardBody}>
              {signIn ? <SignInForm /> : null}
              <SocialAuthButtons />
              <div className={styles.footer}>
                {!signIn ? (
                  <p className={styles.policies}>
                    By continuing, you agree to Heritage’s{" "}
                    {PUBLIC_AUTH_POLICIES.map((policy, index) => (
                      <span key={policy.key}>
                        {index > 0 ? " and " : null}
                        {policy.href ? <Link className={styles.link} href={policy.href}>{policy.label}</Link> : <span className={styles.pendingPolicy} aria-disabled="true" title="Policy link is not available yet">{policy.label}</span>}
                      </span>
                    ))}.
                  </p>
                ) : null}
                <p>
                  {signIn ? "New to Heritage? " : "Already have an account? "}
                  <Link className={styles.link} href={signIn ? PUBLIC_AUTH_ROUTES.register : PUBLIC_AUTH_ROUTES.login}>{signIn ? "Sign up" : "Log in"}</Link>
                </p>
                <Link className={styles.link} href={PUBLIC_ROUTE_BY_KEY.faq.href}>Get help</Link>
              </div>
            </div>
          </section>
        </div>
      </div>
      <aside className={styles.aside} aria-hidden="true">
        <Image src="/figma/auth-cave.png" alt="" fill priority sizes="(min-width: 1024px) 50vw, 1px" className={styles.cave} />
      </aside>
    </main>
  );
}
