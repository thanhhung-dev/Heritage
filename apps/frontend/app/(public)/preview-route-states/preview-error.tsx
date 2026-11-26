"use client";

export function PreviewError() {
  if (typeof window !== "undefined" && sessionStorage.getItem("preview-route-error") === "1") {
    throw new Error("Simulated route render error");
  }
  return <p>Retry completed</p>;
}
