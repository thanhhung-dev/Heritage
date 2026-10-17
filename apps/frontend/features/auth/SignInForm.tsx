"use client";

import { useId, useRef, useState, type FormEvent } from "react";
import Image from "next/image";
import authEye from "@/access/icons/auth-eye.svg";
import { Button, Input, type InputRef } from "antd";
import styles from "./auth.module.css";

function identityError(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "Enter your email or username.";
  if (trimmed.includes("@") && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) return "Enter a valid email address.";
  return "";
}

export function SignInForm() {
  const id = useId();
  const identityRef = useRef<InputRef>(null);
  const passwordRef = useRef<InputRef>(null);
  const [identity, setIdentity] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [touched, setTouched] = useState({ identity: false, password: false });
  const [notice, setNotice] = useState("");
  const emailError = touched.identity ? identityError(identity) : "";
  const passwordError = touched.password && !password ? "Enter your password." : "";

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched({ identity: true, password: true });
    if (identityError(identity)) { identityRef.current?.focus(); return; }
    if (!password) { passwordRef.current?.focus(); return; }
    setNotice("Sign-in is currently unavailable. Please try again later.");
  }

  return (
    <form onSubmit={submit} noValidate className={styles.form}>
      <div className={styles.field}>
        <label htmlFor={`${id}-identity`}>Email or username</label>
        <Input ref={identityRef} id={`${id}-identity`} name="username" autoComplete="username" autoCapitalize="none" spellCheck={false} required className={styles.input} value={identity} aria-invalid={Boolean(emailError)} aria-describedby={`${id}-identity-error`} onChange={event => { setIdentity(event.target.value); setNotice(""); }} onBlur={() => setTouched(previous => ({ ...previous, identity: true }))} />
        <p className={styles.error} id={`${id}-identity-error`} aria-live="polite">{emailError}</p>
      </div>
      <div className={styles.field}>
        <label htmlFor={`${id}-password`}>Password</label>
        <div className={styles.passwordField}>
          <Input ref={passwordRef} id={`${id}-password`} name="password" type={visible ? "text" : "password"} autoComplete="current-password" required className={styles.input} value={password} aria-invalid={Boolean(passwordError)} aria-describedby={`${id}-password-error`} onChange={event => { setPassword(event.target.value); setNotice(""); }} onBlur={() => setTouched(previous => ({ ...previous, password: true }))} />
          <button type="button" className={styles.eye} aria-label={visible ? "Hide password" : "Show password"} aria-pressed={visible} onClick={() => setVisible(previous => !previous)}>
            <Image src={authEye} alt="" aria-hidden="true" width={24} height={24} />
          </button>
        </div>
        <p className={styles.error} id={`${id}-password-error`} aria-live="polite">{passwordError}</p>
      </div>
      <div className={styles.actions}>
        <Button htmlType="submit" type="primary" className={styles.submit} disabled={!identity.trim() || !password}>Log In</Button>
        <Button type="text" className={styles.forgot} onClick={() => setNotice("Password recovery is currently unavailable. Please try again later.")}>Forgot password?</Button>
      </div>
      <p role="status" aria-live="polite" className={notice ? styles.notice : styles.srOnly}>{notice}</p>
    </form>
  );
}
