import { Suspense } from "react";
import { EditDocumentMetadata } from "@/features/knowledge/EditDocumentMetadata";

export default function EditMetadataPage() {
  return <Suspense fallback={<p>Loading document metadata…</p>}><EditDocumentMetadata /></Suspense>;
}
