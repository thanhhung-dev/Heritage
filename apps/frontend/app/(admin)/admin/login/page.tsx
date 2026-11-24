import type { Metadata } from "next";
import { AdminSignIn } from "@/features/admin-auth/AdminSignIn";
import { Suspense } from "react";

export const metadata: Metadata = { title: "Admin Sign In | Heritage" };

export default function AdminSignInPage() {
  return <Suspense><AdminSignIn /></Suspense>;
}
