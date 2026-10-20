import type { Metadata } from "next";
import { ForgotPasswordForm } from "@/features/auth/ForgotPasswordForm";

export const metadata: Metadata = { title: "Forgot Password | Heritage" };

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />;
}
