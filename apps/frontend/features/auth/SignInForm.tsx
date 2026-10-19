"use client";

import { useId, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import authEye from "@/access/icons/auth-eye.svg";
import { Alert, Button, Input, type InputRef } from "antd";
import { handleLogin } from "@/services/authService";
import styles from "./auth.module.css";

function identityError(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "Nhập email hoặc tên đăng nhập của bạn.";
  // Strict email validation as requested
  if (trimmed.includes("@") && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) return "Vui lòng nhập đúng định dạng email (VD: abc@gmail.com)!";
  return "";
}

function passwordError(value: string) {
  if (!value) return "Nhập mật khẩu của bạn.";
  // Min 6 chars validation as requested
  if (value.length < 6) return "Mật khẩu phải có ít nhất 6 ký tự!";
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
  const [apiError, setApiError] = useState("");
  const emailError = touched.identity ? identityError(identity) : "";
  const passwordErr = touched.password ? passwordError(password) : "";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched({ identity: true, password: true });
    setApiError(""); // Clear previous API errors
    
    if (identityError(identity)) { identityRef.current?.focus(); return; }
    if (passwordError(password)) { passwordRef.current?.focus(); return; }
    
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
    } catch (err: any) {
      // Extract specific error message from API response
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || "Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.";
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
          style={{
            backgroundColor: "#ffffff",
            border: "1px solid #ffccc7",
            color: "#cf1322",
            borderRadius: "8px",
            marginBottom: "20px",
            boxShadow: "0 2px 8px rgba(255, 77, 79, 0.08)"
          }}
          closable
          onClose={() => setApiError("")}
        />
      )}
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
        <p className={styles.error} id={`${id}-password-error`} aria-live="polite">{passwordErr}</p>
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
        <Button 
          type="text" 
          className={styles.forgot}
          onClick={() => router.push("/forgot-password")}
        >
          Quên mật khẩu?
        </Button>
      </div>
    </form>
  );
}
