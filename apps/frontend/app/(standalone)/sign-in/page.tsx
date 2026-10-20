import type { Metadata } from "next";
import { AuthScreen } from "@/features/auth/AuthScreen";

export const metadata: Metadata = { title: "Sign In | Heritage" };

export default function SignInPage() {
  return <AuthScreen mode="login" />;
}
