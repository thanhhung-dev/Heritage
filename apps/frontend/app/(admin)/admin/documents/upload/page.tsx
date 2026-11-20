import { Suspense } from "react";
import { UploadDocumentsPage } from "@/features/knowledge/UploadDocumentsPage";

export default function UploadPage() {
  return <Suspense fallback={<p>Loading upload workspace…</p>}><UploadDocumentsPage /></Suspense>;
}
