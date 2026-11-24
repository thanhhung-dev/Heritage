import { notFound } from "next/navigation";
export default async function LoadingPreview() {
  if (process.env.NODE_ENV !== "development") notFound();
  await new Promise((resolve) => setTimeout(resolve, 5000));
  return <main style={{ padding: "120px 24px" }}>Loading completed</main>;
}
