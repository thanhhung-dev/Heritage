"use client";

import { useId, useRef, useState, type CSSProperties, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Image from "next/image";
import { ArrowRightOutlined, CheckCircleOutlined, EyeOutlined, EyeInvisibleOutlined } from "@ant-design/icons";
import { Alert, Button, Input, type InputRef } from "antd";
import logo from "@/access/icons/auth-logo.svg";
import { resetPassword } from "@/services/authService";

const ORANGE = "#f97316";

const inputStyle: CSSProperties = {
  backgroundColor: "#ffffff",
  border: "1px solid #5a6a88",
  borderRadius: "6px",
  height: "44px",
  fontSize: "14px",
  color: "#1f2937",
  fontWeight: 500,
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

function validatePassword(value: string): string {
  if (!value) return "Enter a new password.";
  if (value.length < 12) return "Password must be at least 12 characters long.";

  const hasUpper = /[A-Z]/.test(value);
  const hasLower = /[a-z]/.test(value);
  const hasDigit = /[0-9]/.test(value);
  const hasSpecial = /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(value);

  if (!hasUpper) return "Password must include at least one uppercase letter.";
  if (!hasLower) return "Password must include at least one lowercase letter.";
  if (!hasDigit) return "Password must include at least one number.";
  if (!hasSpecial) return "Password must include at least one special character.";

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
  const [touched, setTouched] = useState({ newPassword: false, confirmPassword: false });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [apiError, setApiError] = useState("");

  const newPasswordError = touched.newPassword ? validatePassword(newPassword) : "";
  const confirmPasswordError = touched.confirmPassword && newPassword !== confirmPassword
    ? "Passwords do not match."
    : "";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTouched({ newPassword: true, confirmPassword: true });
    setApiError("");

    if (!token) {
      setApiError("This reset link is invalid or has expired. Please request a new one.");
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
      const errorMessage =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        "Could not reset your password. Please try again.";
      setApiError(errorMessage);
      console.error("Reset password failed:", err);
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

          <h1 style={{ fontSize: 24, fontWeight: 600, color: "#374151", margin: "0 0 24px" }}>
            Password Reset Successfully!
          </h1>

          <Button
            type="primary"
            style={buttonStyle}
            onClick={() => router.push("/sign-in")}
          >
            Log In Now
          </Button>
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

        <Input.Password
          ref={newPasswordRef}
          id={`${id}-new-password`}
          name="new-password"
          placeholder="New Password"
          autoComplete="new-password"
          required
          status={newPasswordError ? "error" : undefined}
          value={newPassword}
          aria-invalid={Boolean(newPasswordError)}
          iconRender={visible =>
            visible ? (
              <EyeOutlined style={{ color: "#4b5563", fontSize: 16 }} />
            ) : (
              <EyeInvisibleOutlined style={{ color: "#4b5563", fontSize: 16 }} />
            )
          }
          onChange={event => setNewPassword(event.target.value)}
          onBlur={() => setTouched(prev => ({ ...prev, newPassword: true }))}
          style={{ ...inputStyle, marginBottom: 12 }}
        />

        <Input.Password
          ref={confirmPasswordRef}
          id={`${id}-confirm-password`}
          name="confirm-password"
          placeholder="Confirm Password"
          autoComplete="new-password"
          required
          status={confirmPasswordError ? "error" : undefined}
          value={confirmPassword}
          aria-invalid={Boolean(confirmPasswordError)}
          iconRender={visible =>
            visible ? (
              <EyeOutlined style={{ color: "#4b5563", fontSize: 16 }} />
            ) : (
              <EyeInvisibleOutlined style={{ color: "#4b5563", fontSize: 16 }} />
            )
          }
          onChange={event => setConfirmPassword(event.target.value)}
          onBlur={() => setTouched(prev => ({ ...prev, confirmPassword: true }))}
          style={{ ...inputStyle, marginBottom: 16 }}
        />

        <Button
          htmlType="submit"
          type="primary"
          icon={<ArrowRightOutlined />}
          iconPosition="end"
          disabled={!newPassword || !confirmPassword || submitting}
          loading={submitting}
          style={buttonStyle}
        >
          Reset Password
        </Button>

        <p
          style={{
            textAlign: "center",
            fontSize: "12px",
            color: "#9ca3af",
            marginTop: "24px",
            lineHeight: "1.6",
            padding: "0 16px",
          }}
        >
          Note: Password must contain at least 12 characters. Combination of symbols, numbers, uppercase
          letters, lowercase letters.
        </p>
      </form>
    </div>
  );
}

