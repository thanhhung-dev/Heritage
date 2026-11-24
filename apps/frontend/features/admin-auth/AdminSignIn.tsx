"use client";

import { useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Image from "next/image";
import authLogo from "@/access/icons/auth-logo.svg";
import { API_BASE_URL } from "@/config/api";
import { saveAdminSession } from "./admin-session";
import styles from "./admin-sign-in.module.css";

export function AdminSignIn() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [visible, setVisible] = useState(false);
  const [error, setError] = useState(params.get("logout") === "unconfirmed" ? "Your local session was cleared, but the server could not confirm sign out." : "");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    const cleanEmail = email.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) { setError("Enter a valid email address."); return; }
    if (!password) { setError("Enter your password."); return; }
    setError("");
    setSubmitting(true);
    try {
      const response = await fetch(`${API_BASE_URL}/admin/login`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: cleanEmail, password }),
      });
      if (!response.ok) {
        setError(response.status === 403 ? "This account does not have administrator access." : response.status === 401 ? "Incorrect email or password." : "Unable to sign in. Please try again.");
        return;
      }
      const result: unknown = await response.json();
      if (!saveAdminSession(result, remember)) { setError("Unable to verify the admin session."); return; }
      router.replace("/admin");
    } catch {
      setError("Unable to connect. Please try again.");
    } finally { setSubmitting(false); }
  }

  return (
    <main className={styles.screen} lang="en">
      <div className={styles.visual} aria-hidden="true" />
      <section className={styles.panel} aria-labelledby="admin-heading">
        <div className={styles.languages} aria-label="Language">EN <span aria-hidden="true">|</span> <span>VI</span></div>
        <div className={styles.content}>
          <div className={styles.brandRow}>
            <span className={styles.brand}><Image src={authLogo} alt="Heritage" width={103} height={20} /></span>
            <span className={styles.dashboard}>ADMIN DASHBOARD</span>
          </div>
          <h1 id="admin-heading">Welcome to Heritage Admin</h1>
          <form onSubmit={submit} noValidate className={styles.form}>
            <label className={styles.srOnly} htmlFor="admin-email">Email</label>
            <input id="admin-email" type="email" autoComplete="username" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required />
            <div className={styles.password}>
              <label className={styles.srOnly} htmlFor="admin-password">Password</label>
              <input id="admin-password" type={visible ? "text" : "password"} autoComplete="current-password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required />
              <button type="button" className={styles.eye} onClick={() => setVisible(!visible)} aria-label={visible ? "Hide password" : "Show password"} aria-pressed={visible}><Image src="/admin-auth/eye-off.svg" alt="" width={16} height={16} /></button>
            </div>
            <div className={styles.options}><label><input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} /> Remember me</label><span className={styles.unavailable}>Forgot password?</span></div>
            <p className={styles.agreement}>By signing in, you agree to Heritage</p>
            {error && <p className={styles.error} role="alert">{error}</p>}
            <button className={styles.submit} type="submit" disabled={submitting}>{submitting ? "Signing in…" : "Sign in"}</button>
          </form>
          <div className={styles.contact}><p>Need an admin account?</p><p>Contact your administrator for access.</p></div>
        </div>
      </section>
    </main>
  );
}
