/** External reference links never execute script or embed credentials. */
export function safeSourceUrl(value: string | null | undefined): string | null {
  try {
    const url = new URL(value ?? "");
    return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}
