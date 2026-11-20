export const DEFAULT_UPLOAD_LIMIT = 10 * 1024 * 1024;
export const UPLOAD_MIME_TYPES: Readonly<Record<string, string>> = {
  md: "text/markdown", txt: "text/plain", json: "application/json",
};
export const UPLOAD_ACCEPT = ".md,.txt,.json";

export function uploadFileType(file: Pick<File, "name" | "size">): string {
  const name = file.name;
  if (!name || name !== name.trim() || name !== name.normalize("NFC")
      || new TextEncoder().encode(name).length > 255
      || /[/\\%?#":*<>|\p{Cc}\p{Cf}\p{Cs}]/u.test(name)) {
    throw new Error("Use an NFC Unicode filename without path, control characters or surrounding spaces.");
  }
  const type = UPLOAD_MIME_TYPES[name.split(".").pop()?.toLowerCase() ?? ""];
  if (!type) throw new Error("Choose a Markdown (.md), text (.txt) or JSON (.json) file.");
  if (!Number.isSafeInteger(file.size) || file.size <= 0 || file.size > DEFAULT_UPLOAD_LIMIT) {
    throw new Error("Choose a non-empty file up to 10 MiB (the default server limit).");
  }
  return type;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${Number((bytes / 1024).toFixed(1))} KiB`;
  return `${Number((bytes / 1024 ** 2).toFixed(1))} MiB`;
}
