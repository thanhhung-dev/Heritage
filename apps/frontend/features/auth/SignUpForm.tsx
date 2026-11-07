"use client";

import { useId, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import authEye from "@/access/icons/auth-eye.svg";
import { Alert, Button, Input, type InputRef } from "antd";
import { handleRegister } from "@/services/authService";
import styles from "./auth.module.css";

function emailError(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "Enter your email.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) return "Enter a valid email address.";
  return "";
}

function usernameError(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "Enter a username.";
  if (trimmed.length < 3) return "Username must be at least 3 characters.";
  if (!/^[a-zA-Z0-9_-]+$/.test(trimmed)) return "Username can only contain letters, numbers, _ and -.";
  return "";
}

function passwordError(value: string) {
  if (!value) return "Enter your password.";
  if (value.length < 6) return "Password must be at least 6 characters.";
  return "";
}

export function SignUpForm() {
  const id = useId();
  const router = useRouter();
  const emailRef = useRef<InputRef>(null);
  const usernameRef = useRef<InputRef>(null);
  const passwordRef = useRef<InputRef>(null);
  
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [touched, setTouched] = useState({ email: false, username: false, password: false });
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState("");
  
  const emailErr = touched.email ? emailError(email) : "";
  const usernameErr = touched.username ? usernameError(username) : "";
  const passwordErr = touched.password ? passwordError(password) : "";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched({ email: true, username: true, password: true });
    setApiError(""); // Clear previous API errors
    
    // Validation
    if (emailError(email)) { emailRef.current?.focus(); return; }
    if (usernameError(username)) { usernameRef.current?.focus(); return; }
    if (passwordError(password)) { passwordRef.current?.focus(); return; }
    
    setSubmitting(true);
    try {
      await handleRegister(
        {
          email: email.trim(),
          username: username.trim(),
          password,
        },
        () => {
          // Redirect to sign-in page on success
          router.push("/sign-in");
        }
      );
    } catch (err: any) {
      // Extract specific error message from API response
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || "Something went wrong. Please try again.";
      setApiError(errorMessage);
      console.error("Registration failed:", err);
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
        <label htmlFor={`${id}-username`}>Username</label>
        <Input
          ref={usernameRef}
          id={`${id}-username`}
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          className={styles.input}
          value={username}
          aria-invalid={Boolean(usernameErr)}
          aria-describedby={`${id}-username-error`}
          onChange={event => setUsername(event.target.value)}
          onBlur={() => setTouched(previous => ({ ...previous, username: true }))}
        />
        <p className={styles.error} id={`${id}-username-error`} aria-live="polite">{usernameErr}</p>
      </div>
      
      <div className={styles.field}>
        <label htmlFor={`${id}-password`}>Password</label>
        <div className={styles.passwordField}>
          <Input
            ref={passwordRef}
            id={`${id}-password`}
            name="password"
            type={visible ? "text" : "password"}
            autoComplete="new-password"
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
          disabled={!email.trim() || !username.trim() || !password || submitting}
          loading={submitting}
        >
          Sign Up
        </Button>
      </div>
    </form>
  );
}
