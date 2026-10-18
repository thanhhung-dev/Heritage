"use client";

import { useId, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import authEye from "@/access/icons/auth-eye.svg";
import { Button, Input, type InputRef } from "antd";
import { handleLogin } from "@/services/authService";
import styles from "./auth.module.css";

function identityError(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "Nhập email hoặc tên đăng nhập của bạn.";
  if (trimmed.includes("@") && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) return "Nhập địa chỉ email hợp lệ.";
  return "";
}

export function SignInForm() {
  const id = useId();
  const router = useRouter();
  const identityRef = useRef<InputRef>(null);
  const passwordRef = useRef<InputRef>(null);
  const [identity, setIdentity] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [touched, setTouched] = useState({ identity: false, password: false });
  const [submitting, setSubmitting] = useState(false);
  const emailError = touched.identity ? identityError(identity) : "";
  const passwordError = touched.password && !password ? "Nhập mật khẩu của bạn." : "";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched({ identity: true, password: true });
    if (identityError(identity)) { identityRef.current?.focus(); return; }
    if (!password) { passwordRef.current?.focus(); return; }
    
    setSubmitting(true);
    try {
      await handleLogin(
        {
          username_or_email: identity.trim(),
          password,
        },
        () => {
          // Redirect to home page on success
          router.push("/");
        }
      );
    } catch (error) {
      // Error already displayed by handleLogin
      console.error("Login failed:", error);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className={styles.form}>
      <div className={styles.field}>
        <label htmlFor={`${id}-identity`}>Email hoặc tên đăng nhập</label>
        <Input
          ref={identityRef}
          id={`${id}-identity`}
          name="username"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          className={styles.input}
          value={identity}
          aria-invalid={Boolean(emailError)}
          aria-describedby={`${id}-identity-error`}
          onChange={event => setIdentity(event.target.value)}
          onBlur={() => setTouched(previous => ({ ...previous, identity: true }))}
        />
        <p className={styles.error} id={`${id}-identity-error`} aria-live="polite">{emailError}</p>
      </div>
      <div className={styles.field}>
        <label htmlFor={`${id}-password`}>Mật khẩu</label>
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
            aria-invalid={Boolean(passwordError)}
            aria-describedby={`${id}-password-error`}
            onChange={event => setPassword(event.target.value)}
            onBlur={() => setTouched(previous => ({ ...previous, password: true }))}
          />
          <button
            type="button"
            className={styles.eye}
            aria-label={visible ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
            aria-pressed={visible}
            onClick={() => setVisible(previous => !previous)}
          >
            <Image src={authEye} alt="" aria-hidden="true" width={24} height={24} />
          </button>
        </div>
        <p className={styles.error} id={`${id}-password-error`} aria-live="polite">{passwordError}</p>
      </div>
      <div className={styles.actions}>
        <Button
          htmlType="submit"
          type="primary"
          className={styles.submit}
          disabled={!identity.trim() || !password || submitting}
          loading={submitting}
        >
          Đăng nhập
        </Button>
        <Button type="text" className={styles.forgot} disabled>Quên mật khẩu?</Button>
      </div>
    </form>
  );
}
