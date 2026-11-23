"use client";

import { useId, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import authEye from "@/access/icons/auth-eye.svg";
import { Button, Input, type InputRef } from "antd";
import { registerUser } from "@/services/authService";
import { AuthApiError, type AuthFieldErrors } from "@/services/auth-api";
import { emailError, usernameError, passwordError, registrationSignInHref } from "./auth-validation";
import styles from "./auth.module.css";

export function SignUpForm() {
  const id = useId();
  const router = useRouter();
  const emailRef = useRef<InputRef>(null);
  const usernameRef = useRef<InputRef>(null);
  const passwordRef = useRef<InputRef>(null);
  const pending = useRef(false);
  
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [touched, setTouched] = useState({ email: false, username: false, password: false });
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState("");
  const [apiFields, setApiFields] = useState<AuthFieldErrors>({});
  
  const emailErr = (touched.email ? emailError(email) : "") || apiFields.email;
  const usernameErr = (touched.username ? usernameError(username) : "") || apiFields.username;
  const passwordErr = (touched.password ? passwordError(password, true) : "") || apiFields.password;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending.current) return;
    setTouched({ email: true, username: true, password: true });
    setApiError(""); // Clear previous API errors
    setApiFields({});
    
    // Validation
    if (emailError(email)) { emailRef.current?.focus(); return; }
    if (usernameError(username)) { usernameRef.current?.focus(); return; }
    if (passwordError(password, true)) { passwordRef.current?.focus(); return; }
    
    setSubmitting(true);
    pending.current = true;
    let succeeded = false;
    try {
      await registerUser({ email, username, password });
      router.push(registrationSignInHref(new URLSearchParams(window.location.search).get("next")));
      succeeded = true;
    } catch (error: unknown) {
      setApiError(error instanceof Error ? error.message : "Registration failed. Please try again.");
      if (error instanceof AuthApiError) {
        setApiFields(error.fields);
        if (error.fields.email) emailRef.current?.focus();
        else if (error.fields.username) usernameRef.current?.focus();
        else if (error.fields.password) passwordRef.current?.focus();
      }
    } finally {
      if (!succeeded) { pending.current = false; setSubmitting(false); }
    }
  }

  return (
    <form onSubmit={submit} noValidate className={styles.form} aria-busy={submitting}>
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
        <label htmlFor={`${id}-username`}>Username</label>
        <Input
          ref={usernameRef}
          id={`${id}-username`}
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          disabled={submitting}
          className={styles.input}
          value={username}
          aria-invalid={Boolean(usernameErr)}
          aria-describedby={`${id}-username-error`}
          onChange={event => { setUsername(event.target.value); setApiError(""); setApiFields(previous => ({ ...previous, username: undefined })); }}
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
            disabled={submitting}
            className={styles.input}
            value={password}
            aria-invalid={Boolean(passwordErr)}
            aria-describedby={`${id}-password-hint ${id}-password-error`}
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
        <p className={styles.hint} id={`${id}-password-hint`}>Use at least 8 characters.</p>
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
