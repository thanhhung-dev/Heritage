import type { Metadata } from "next";
import { AuthScreen } from "@/features/auth/AuthScreen";

export const metadata: Metadata = { title: "Sign Up | Heritage" };

export default function SignUpPage() {
  return <AuthScreen mode="register" />;
}
