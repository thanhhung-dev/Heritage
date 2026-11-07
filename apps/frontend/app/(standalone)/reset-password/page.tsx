import type { Metadata } from "next";
import { Suspense } from "react";
import BrandTextLoading from "@/components/Loading/BrandTextLoading";
import { ResetPasswordForm } from "@/features/auth/ResetPasswordForm";

export const metadata: Metadata = { title: "Reset Password | Heritage" };

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<BrandTextLoading label="Loading reset password…" />}>
      <ResetPasswordForm />
    </Suspense>
  );
}
