"use client";

import { useId, useRef, useState, type CSSProperties, type FormEvent } from "react";
import Link from "next/link";
import Image from "next/image";
import { ArrowRightOutlined, CheckCircleOutlined } from "@ant-design/icons";
import { Alert, Button, Input, type InputRef } from "antd";
import logo from "@/access/icons/auth-logo.svg";
import { forgotPassword } from "@/services/authService";

const ORANGE = "#f97316";

const inputStyle: CSSProperties = {
  backgroundColor: "#ffffff",
  border: "1px solid #e5e7eb",
  borderRadius: "6px",
  height: "44px",
  fontSize: "14px",
  color: "#1f2937",
  boxShadow: "none",
};

const buttonStyle: CSSProperties = {
  backgroundColor: ORANGE,
  border: "none",
  borderRadius: "6px",
  height: "44px",
  color: "#ffffff",
  fontWeight: 500,
  fontSize: "14px",
  width: "100%",
  boxShadow: "none",
};

function emailError(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "Enter your email address.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) return "Enter a valid email address.";
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
      await forgotPassword(email.trim());
      setSubmittedEmail(email.trim()); // Store the email for success display
      setSubmitted(true);
    } catch (err: any) {
      // Extract specific error message from API response
      const errorMessage =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        "Something went wrong. Please try again.";
      setApiError(errorMessage);
      console.error("Forgot password failed:", err);
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div
        style={{
          minHeight: "100vh",
          backgroundColor: "#ffffff",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          paddingTop: "6vh",
        }}
      >
        <div style={{ width: "100%", maxWidth: "400px", padding: "0 20px", textAlign: "center" }}>
          <Image
            src={logo}
            alt="Heritage"
            style={{ height: 32, width: "auto", marginBottom: 40 }}
            width={103}
            height={32}
            priority
          />

          <CheckCircleOutlined style={{ fontSize: 48, color: "#22c55e", marginBottom: 20 }} />

          <h1 style={{ fontSize: 24, fontWeight: 600, color: "#374151", margin: "0 0 12px" }}>
            Check your email
          </h1>

          <p style={{ fontSize: 13, color: "#6b7280", margin: "0 0 24px", lineHeight: 1.6 }}>
            We sent a password reset link to{" "}
            <strong style={{ color: "#ea580c", fontWeight: 600 }}>{submittedEmail}</strong>
          </p>

          <div
            style={{
              backgroundColor: "#f9fafb",
              border: "1px solid #e5e7eb",
              borderRadius: 6,
              padding: "12px 16px",
              marginBottom: 24,
            }}
          >
            <p style={{ margin: 0, fontSize: 13, color: "#6b7280" }}>
              Didn&apos;t receive the email? Check your spam folder.
            </p>
          </div>

          <Link href="/sign-in" style={{ textDecoration: "none" }}>
            <Button type="primary" style={buttonStyle}>
              Back to Log in
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#ffffff",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        paddingTop: "6vh",
      }}
    >
      <form onSubmit={submit} noValidate style={{ width: "100%", maxWidth: "400px", padding: "0 20px" }}>
        <Image
          src={logo}
          alt="Heritage"
          style={{ display: "block", height: 32, width: "auto", margin: "0 auto 40px" }}
          width={103}
          height={32}
          priority
        />

        <h1 style={{ textAlign: "center", fontSize: 24, fontWeight: 600, color: "#374151", margin: "0 0 24px" }}>
          Reset Password
        </h1>

        <p style={{ textAlign: "left", fontSize: 13, color: "#6b7280", margin: "0 0 8px" }}>
          We&apos;ll email you a password reset link
        </p>

        {apiError && (
          <Alert
            showIcon
            type="error"
            message={apiError}
            style={{
              backgroundColor: "#ffffff",
              border: "1px solid #fecaca",
              color: "#dc2626",
              borderRadius: 6,
              marginBottom: 16,
              textAlign: "left",
            }}
            closable
            onClose={() => setApiError("")}
          />
        )}

        <Input
          ref={emailRef}
          id={`${id}-email`}
          name="email"
          type="email"
          autoComplete="email"
          autoCapitalize="none"
          spellCheck={false}
          required
          placeholder="email@example.com"
          value={email}
          aria-invalid={Boolean(error)}
          onChange={event => setEmail(event.target.value)}
          onBlur={() => setTouched(true)}
          style={{ ...inputStyle, marginBottom: 24 }}
        />

        <Button
          htmlType="submit"
          type="primary"
          icon={<ArrowRightOutlined />}
          iconPosition="end"
          disabled={!email.trim() || submitting}
          loading={submitting}
          style={buttonStyle}
        >
          Start Reset Password
        </Button>
      </form>
    </div>
  );
}
