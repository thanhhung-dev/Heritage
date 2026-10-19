"use client";

import { useId, useRef, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Image from "next/image";
import authEye from "@/access/icons/auth-eye.svg";
import { Alert, Button, Card, Input, Result, type InputRef } from "antd";
import { resetPassword } from "@/services/authService";
import styles from "./auth.module.css";

function validatePassword(value: string): string {
  if (!value) return "Nhập mật khẩu mới.";
  if (value.length < 12) return "Mật khẩu phải có ít nhất 12 ký tự.";
  
  const hasUpper = /[A-Z]/.test(value);
  const hasLower = /[a-z]/.test(value);
  const hasDigit = /[0-9]/.test(value);
  const hasSpecial = /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(value);
  
  if (!hasUpper) return "Mật khẩu phải có ít nhất một chữ hoa.";
  if (!hasLower) return "Mật khẩu phải có ít nhất một chữ thường.";
  if (!hasDigit) return "Mật khẩu phải có ít nhất một số.";
  if (!hasSpecial) return "Mật khẩu phải có ít nhất một ký tự đặc biệt.";
  
  return "";
}

export function ResetPasswordForm() {
  const id = useId();
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  
  const newPasswordRef = useRef<InputRef>(null);
  const confirmPasswordRef = useRef<InputRef>(null);
  
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [visibleNew, setVisibleNew] = useState(false);
  const [visibleConfirm, setVisibleConfirm] = useState(false);
  const [touched, setTouched] = useState({ newPassword: false, confirmPassword: false });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [apiError, setApiError] = useState("");
  
  const newPasswordError = touched.newPassword ? validatePassword(newPassword) : "";
  const confirmPasswordError = touched.confirmPassword && newPassword !== confirmPassword 
    ? "Mật khẩu xác nhận không khớp." 
    : "";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched({ newPassword: true, confirmPassword: true });
    setApiError("");
    
    if (!token) {
      setApiError("Token không hợp lệ hoặc đã hết hạn. Vui lòng yêu cầu đặt lại mật khẩu mới.");
      return;
    }
    
    if (validatePassword(newPassword)) {
      newPasswordRef.current?.focus();
      return;
    }
    
    if (newPassword !== confirmPassword) {
      confirmPasswordRef.current?.focus();
      return;
    }
    
    setSubmitting(true);
    try {
      await resetPassword(token, newPassword);
      setSubmitted(true);
    } catch (err: any) {
      const errorMessage = err?.message || "Đặt lại mật khẩu thất bại. Vui lòng thử lại sau.";
      setApiError(errorMessage);
      console.error("Reset password failed:", err);
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className={styles.form}>
        <Card
          style={{
            backgroundColor: "#ffffff",
            border: "1px solid #e5e7eb",
            borderRadius: "12px",
            boxShadow: "0 4px 16px rgba(0, 0, 0, 0.08)",
            padding: "16px"
          }}
          bodyStyle={{ padding: "24px" }}
        >
          <Result
            status="success"
            title={
              <span style={{ 
                color: "#111827", 
                fontWeight: 700, 
                fontSize: "22px",
                display: "block",
                marginBottom: "12px"
              }}>
                Đặt lại mật khẩu thành công!
              </span>
            }
            subTitle={
              <div style={{ 
                color: "#374151", 
                fontSize: "15px", 
                lineHeight: 1.6,
                textAlign: "left"
              }}>
                <p style={{ margin: 0 }}>
                  Mật khẩu của bạn đã được cập nhật. Vui lòng đăng nhập lại bằng mật khẩu mới.
                </p>
              </div>
            }
            style={{
              padding: "0"
            }}
            extra={
              <Button
                type="primary"
                className={styles.submit}
                style={{ width: "100%" }}
                onClick={() => router.push("/sign-in")}
              >
                Đăng nhập ngay
              </Button>
            }
          />
        </Card>
      </div>
    );
  }

  if (!token) {
    return (
      <div className={styles.form}>
        <Alert
          showIcon
          type="error"
          message="Token không hợp lệ hoặc đã hết hạn. Vui lòng yêu cầu đặt lại mật khẩu mới."
          style={{
            backgroundColor: "#ffffff",
            border: "1px solid #ffccc7",
            color: "#cf1322",
            borderRadius: "8px",
            marginBottom: "20px",
            boxShadow: "0 2px 8px rgba(255, 77, 79, 0.08)"
          }}
        />
      </div>
    );
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
        <label htmlFor={`${id}-new-password`}>Mật khẩu mới</label>
        <div className={styles.passwordField}>
          <Input
            ref={newPasswordRef}
            id={`${id}-new-password`}
            name="new-password"
            type={visibleNew ? "text" : "password"}
            autoComplete="new-password"
            required
            className={styles.input}
            value={newPassword}
            aria-invalid={Boolean(newPasswordError)}
            aria-describedby={`${id}-new-password-error`}
            onChange={event => setNewPassword(event.target.value)}
            onBlur={() => setTouched(prev => ({ ...prev, newPassword: true }))}
          />
          <button
            type="button"
            className={styles.eye}
            aria-label={visibleNew ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
            aria-pressed={visibleNew}
            onClick={() => setVisibleNew(prev => !prev)}
          >
            <Image src={authEye} alt="" aria-hidden="true" width={24} height={24} />
          </button>
        </div>
        <p className={styles.error} id={`${id}-new-password-error`} aria-live="polite">
          {newPasswordError}
        </p>
      </div>
      
      <div className={styles.field}>
        <label htmlFor={`${id}-confirm-password`}>Xác nhận mật khẩu</label>
        <div className={styles.passwordField}>
          <Input
            ref={confirmPasswordRef}
            id={`${id}-confirm-password`}
            name="confirm-password"
            type={visibleConfirm ? "text" : "password"}
            autoComplete="new-password"
            required
            className={styles.input}
            value={confirmPassword}
            aria-invalid={Boolean(confirmPasswordError)}
            aria-describedby={`${id}-confirm-password-error`}
            onChange={event => setConfirmPassword(event.target.value)}
            onBlur={() => setTouched(prev => ({ ...prev, confirmPassword: true }))}
          />
          <button
            type="button"
            className={styles.eye}
            aria-label={visibleConfirm ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
            aria-pressed={visibleConfirm}
            onClick={() => setVisibleConfirm(prev => !prev)}
          >
            <Image src={authEye} alt="" aria-hidden="true" width={24} height={24} />
          </button>
        </div>
        <p className={styles.error} id={`${id}-confirm-password-error`} aria-live="polite">
          {confirmPasswordError}
        </p>
      </div>
      
      <p style={{ margin: "4px 0 0", fontSize: "11px", lineHeight: "18px", color: "var(--auth-label)" }}>
        <strong>Lưu ý:</strong> Mật khẩu phải có ít nhất 12 ký tự. Bao gồm chữ hoa, chữ thường, số và ký tự đặc biệt.
      </p>
      
      <div className={styles.actions}>
        <Button
          htmlType="submit"
          type="primary"
          className={styles.submit}
          disabled={!newPassword || !confirmPassword || submitting}
          loading={submitting}
        >
          Đặt lại mật khẩu
        </Button>
      </div>
    </form>
  );
}

