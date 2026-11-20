import { Suspense } from "react";
import { DocumentLibrary } from "@/features/knowledge/DocumentLibrary";

export default function DocumentsPage() {
  return <Suspense fallback={<p>Loading document library…</p>}><DocumentLibrary /></Suspense>;
}
