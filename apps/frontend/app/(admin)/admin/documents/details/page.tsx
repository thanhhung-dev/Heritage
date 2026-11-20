import { Suspense } from "react";
import { DocumentDetails } from "@/features/knowledge/DocumentDetails";

export default function DocumentDetailsPage() {
  return <Suspense fallback={<p>Loading document details…</p>}><DocumentDetails /></Suspense>;
}
