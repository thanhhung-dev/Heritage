"use client";

import { useId, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import authEye from "@/access/icons/auth-eye.svg";
import { Alert, Button, Input, type InputRef } from "antd";
import { handleLogin } from "@/services/authService";
import styles from "./auth.module.css";

function emailError(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "Enter your email.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
    return "Enter a valid email address.";
  }
  return "";
}

function passwordError(value: string) {
  if (!value) return "Enter your password.";
  if (value.length < 6) return "Password must be at least 6 characters.";
  return "";
}

export function SignInForm() {
  const id = useId();
  const router = useRouter();
  const emailRef = useRef<InputRef>(null);
  const passwordRef = useRef<InputRef>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [touched, setTouched] = useState({ email: false, password: false });
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState("");
  const emailErr = touched.email ? emailError(email) : "";
  const passwordErr = touched.password ? passwordError(password) : "";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched({ email: true, password: true });
    setApiError("");

    if (emailError(email)) { emailRef.current?.focus(); return; }
    if (passwordError(password)) { passwordRef.current?.focus(); return; }
    
    setSubmitting(true);
    try {
      await handleLogin(
        {
          email: email.trim(),
          password,
        },
        () => {
          // Redirect to home page on success
          router.push("/");
        }
      );
    } catch (err: any) {
      // Extract specific error message from API response
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || "Something went wrong. Please try again.";
      setApiError(errorMessage);
      console.error("Login failed:", err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className={styles.form}>
      {apiError && (
        <Alert
          showIcon
          type="error"
          message={apiError}
          className={styles.alert}
          closable
          onClose={() => setApiError("")}
        />
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
          className={styles.input}
          value={email}
          aria-invalid={Boolean(emailErr)}
          aria-describedby={`${id}-email-error`}
          onChange={event => setEmail(event.target.value)}
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
            className={styles.input}
            value={password}
            aria-invalid={Boolean(passwordErr)}
            aria-describedby={`${id}-password-error`}
            onChange={event => setPassword(event.target.value)}
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
