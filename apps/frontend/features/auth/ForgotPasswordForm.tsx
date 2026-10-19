"use client";

import { useId, useRef, useState, type FormEvent } from "react";
import { Alert, Button, Card, Input, Result, type InputRef } from "antd";
import { forgotPassword } from "@/services/authService";
import styles from "./auth.module.css";

function emailError(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "Nhập địa chỉ email của bạn.";
  // Strict email validation as requested
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) return "Vui lòng nhập đúng định dạng email (VD: abc@gmail.com)!";
  return "";
}

export function ForgotPasswordForm() {
  const id = useId();
  const emailRef = useRef<InputRef>(null);
  const [email, setEmail] = useState("");
  const [submittedEmail, setSubmittedEmail] = useState(""); // Store submitted email for display
  const [touched, setTouched] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [apiError, setApiError] = useState("");
  const error = touched ? emailError(email) : "";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched(true);
    setApiError(""); // Clear previous API errors
    
    if (emailError(email)) {
      emailRef.current?.focus();
      return;
    }
    
    setSubmitting(true);
    try {
      const response = await forgotPassword(email.trim());
      setSubmittedEmail(email.trim()); // Store the email for success display
      setSubmitted(true);
    } catch (err: any) {
      // Extract specific error message from API response
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || "Đã xảy ra lỗi hệ thống. Vui lòng thử lại sau.";
      setApiError(errorMessage);
      console.error("Forgot password failed:", err);
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
                Yêu cầu đã được gửi thành công!
              </span>
            }
            subTitle={
              <div style={{ 
                color: "#374151", 
                fontSize: "15px", 
                lineHeight: 1.6,
                textAlign: "left"
              }}>
                <p style={{ marginBottom: "16px" }}>
                  Hướng dẫn khôi phục mật khẩu đã được gửi đến địa chỉ email: <strong style={{ color: "#ea580c", fontWeight: 600 }}>{submittedEmail}</strong>
                </p>
                <p style={{ marginBottom: "16px" }}>
                  Vui lòng kiểm tra hòm thư và làm theo hướng dẫn để đặt lại mật khẩu của bạn.
                </p>
                <div style={{
                  backgroundColor: "#f9fafb",
                  border: "1px solid #e5e7eb",
                  borderRadius: "8px",
                  padding: "12px 16px",
                  marginTop: "16px"
                }}>
                  <p style={{ 
                    margin: 0, 
                    fontSize: "14px",
                    color: "#374151"
                  }}>
                    <strong>💡 Lưu ý:</strong> Vui lòng kiểm tra cả hòm thư Thư rác / Spam nếu không thấy email trong Hộp thư đến.
                  </p>
                </div>
              </div>
            }
            style={{
              padding: "0"
            }}
          />
        </Card>
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
        <label htmlFor={`${id}-email`}>Địa chỉ email</label>
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
          aria-invalid={Boolean(error)}
          aria-describedby={`${id}-email-error`}
          onChange={event => setEmail(event.target.value)}
          onBlur={() => setTouched(true)}
        />
        <p className={styles.error} id={`${id}-email-error`} aria-live="polite">{error}</p>
      </div>
      <div className={styles.actions}>
        <Button
          htmlType="submit"
          type="primary"
          className={styles.submit}
          disabled={!email.trim() || submitting}
          loading={submitting}
        >
          Gửi link khôi phục
        </Button>
      </div>
    </form>
  );
}
