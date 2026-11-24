import { notFound } from "next/navigation";
import Link from "next/link";
import { PreviewError } from "./preview-error";
import { ErrorTrigger } from "./error-trigger";
export default function PreviewRouteStates({ searchParams }: { searchParams: { mode?: string } }) {
  if (process.env.NODE_ENV !== "development") notFound();
  return <div style={{ padding: "120px 24px", minHeight: "60vh" }}>
    <h1>Route state preview</h1><p>Development-only simulation. Wait 5 seconds before retrying.</p>
    <Link href="/preview-route-states/loading" prefetch={false}>Test loading</Link>{" · "}<ErrorTrigger />
    {searchParams.mode === "error" && <PreviewError />}
  </div>;
}
