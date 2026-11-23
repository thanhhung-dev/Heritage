"use client";

import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import authEye from "@/access/icons/auth-eye.svg";
import { Button, Input, type InputRef } from "antd";
import { loginUser } from "@/services/authService";
import { AuthApiError, type AuthFieldErrors } from "@/services/auth-api";
import { setAuthTokens } from "@/lib/auth";
import { emailError, passwordError, safeAuthNext } from "./auth-validation";
import styles from "./auth.module.css";

export function SignInForm() {
  const id = useId();
  const router = useRouter();
  const emailRef = useRef<InputRef>(null);
  const passwordRef = useRef<InputRef>(null);
  const pending = useRef(false);
  const [registered, setRegistered] = useState(false);
  useEffect(() => { setRegistered(new URLSearchParams(window.location.search).get("registered") === "1"); }, []);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [touched, setTouched] = useState({ email: false, password: false });
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState("");
  const [apiFields, setApiFields] = useState<AuthFieldErrors>({});
  useEffect(() => {
    if (submitting) return;
    if (apiFields.email) emailRef.current?.focus();
    else if (apiFields.password) passwordRef.current?.focus();
  }, [apiFields, submitting]);
  const emailErr = (touched.email ? emailError(email) : "") || apiFields.email;
  const passwordErr = (touched.password ? passwordError(password) : "") || apiFields.password;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current) return;
    setTouched({ email: true, password: true });
    setApiError("");
    setApiFields({});

    if (emailError(email)) { emailRef.current?.focus(); return; }
    if (passwordError(password)) { passwordRef.current?.focus(); return; }
    
    setSubmitting(true);
    pending.current = true;
    let succeeded = false;
    try {
      const response = await loginUser({ email, password });
      try { setAuthTokens(response); }
      catch { throw new Error("Your browser could not save the session. Allow site storage and try again."); }
      router.push(safeAuthNext(new URLSearchParams(window.location.search).get("next")));
      succeeded = true;
    } catch (error: unknown) {
      setApiError(error instanceof Error ? error.message : "Could not sign in. Please try again.");
      if (error instanceof AuthApiError) setApiFields(error.fields);
    } finally {
      if (!succeeded) { pending.current = false; setSubmitting(false); }
    }
  }

  return (
    <form method="post" onSubmit={submit} noValidate className={styles.form} aria-busy={submitting}>
      {registered && <div role="status" className={styles.success}>Account created successfully. Sign in with your email and password.</div>}
      {apiError && (
        <div role="alert" className={styles.alert}>{apiError}</div>
      )}
      <div className={styles.field}>
        <label htmlFor={`${id}-email`}>Email</label>
        <Input
          ref={emailRef}
          id={`${id}-email`}
          name="email"
          type="email"
          autoComplete="email"
          autoCapitalize="none"
          spellCheck={false}
          required
          disabled={submitting}
          className={styles.input}
          value={email}
          aria-invalid={Boolean(emailErr)}
          aria-describedby={`${id}-email-error`}
          onChange={event => { setEmail(event.target.value); setApiError(""); setApiFields(previous => ({ ...previous, email: undefined })); }}
          onBlur={() => setTouched(previous => ({ ...previous, email: true }))}
        />
        <p className={styles.error} id={`${id}-email-error`} aria-live="polite">{emailErr}</p>
      </div>
      <div className={styles.field}>
        <label htmlFor={`${id}-password`}>Password</label>
        <div className={styles.passwordField}>
          <Input
            ref={passwordRef}
            id={`${id}-password`}
            name="password"
            type={visible ? "text" : "password"}
            autoComplete="current-password"
            required
            disabled={submitting}
            className={styles.input}
            value={password}
            aria-invalid={Boolean(passwordErr)}
            aria-describedby={`${id}-password-error`}
            onChange={event => { setPassword(event.target.value); setApiError(""); setApiFields(previous => ({ ...previous, password: undefined })); }}
            onBlur={() => setTouched(previous => ({ ...previous, password: true }))}
          />
          <button
            type="button"
            className={styles.eye}
            aria-label={visible ? "Hide password" : "Show password"}
            aria-pressed={visible}
            onClick={() => setVisible(previous => !previous)}
          >
            <Image src={authEye} alt="" aria-hidden="true" width={24} height={24} />
          </button>
        </div>
        <p className={styles.error} id={`${id}-password-error`} aria-live="polite">{passwordErr}</p>
      </div>
      <div className={styles.actions}>
        <Button
          htmlType="submit"
          type="primary"
          className={styles.submit}
          disabled={!email.trim() || !password || submitting}
          loading={submitting}
        >
          Log In
        </Button>
        <Button
          type="text"
          className={styles.forgot}
          onClick={() => router.push("/forgot-password")}
        >
          Forgot password?
        </Button>
      </div>
    </form>
  );
}
