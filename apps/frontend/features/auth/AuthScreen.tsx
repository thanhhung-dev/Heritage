import Image from "next/image";
import Link from "next/link";
import { HeritageLogo } from "@/components/Logo/HeritageLogo";
import logoText from "@/access/icons/logo-text.svg";
import authCave from "@/access/images/auth-cave.png";
import { PUBLIC_AUTH_POLICIES, PUBLIC_AUTH_ROUTES } from "@/config/public-auth";
import { PUBLIC_ROUTE_BY_KEY } from "@/config/public-navigation";
import type { AuthMode } from "./types";
import { SignInForm } from "./SignInForm";
import { SignUpForm } from "./SignUpForm";
import { SocialAuthButtons } from "./SocialAuthButtons";
import styles from "./auth.module.css";

export function AuthScreen({ mode }: { mode: AuthMode }) {
  const signIn = mode === "login";

  return (
    <main className={styles.screen} lang="en">
      <div className={styles.main}>
        <header className={styles.brandRow}>
          <Link href={PUBLIC_ROUTE_BY_KEY.home.href} aria-label="Heritage home" className={styles.brand}>
            <HeritageLogo size={20} />
            <Image src={logoText} alt="Heritage" width={100} height={20} priority className={styles.brandWordmark} />
          </Link>
        </header>
        <div className={styles.center}>
          <section className={styles.card} aria-labelledby="auth-heading">
            <h1 id="auth-heading" className={styles.heading}>
              {signIn ? "Log in to your account" : "Create your Heritage account"}
            </h1>
            <div className={styles.cardBody}>
              {signIn ? <SignInForm /> : <SignUpForm />}
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
                <Link className={styles.helpLink} href={PUBLIC_ROUTE_BY_KEY.faq.href}>Get help</Link>
              </div>
            </div>
          </section>
        </div>
      </div>
      <aside className={styles.aside} aria-hidden="true">
        <Image
          src={authCave}
          alt=""
          fill
          priority
          sizes="(min-width: 900px) 50vw, 1px"
          className={styles.cave}
        />
        <div className={styles.asideOverlay}>
          <span className={styles.asideTitle}>History lives on</span>
          <Image src={logoText} alt="" width={148} height={30} className={styles.asideWordmark} />
        </div>
      </aside>
    </main>
  );
}
