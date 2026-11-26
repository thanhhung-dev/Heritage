"use client";
import { useRouter } from "next/navigation";
export function ErrorTrigger() {
  const router = useRouter();
  return <button onClick={() => {
    sessionStorage.setItem("preview-route-error", "1");
    setTimeout(() => sessionStorage.removeItem("preview-route-error"), 5000);
    router.push("/preview-route-states?mode=error");
  }}>Test error and retry</button>;
}
