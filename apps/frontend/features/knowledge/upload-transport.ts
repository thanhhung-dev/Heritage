import type { KnowledgeUploadTicket } from "./types";

export class R2TransferError extends Error {
  constructor(message: string, readonly status: number) { super(message); this.name = "R2TransferError"; }
}

export type UploadProgress = { loaded: number; total: number };
export type DirectUpload = (ticket: KnowledgeUploadTicket, file: File, signal: AbortSignal,
  onProgress: (progress: UploadProgress) => void) => Promise<void>;

/** Deliberately bypasses apiFetch: an Admin JWT must never reach object storage. */
export function createDirectUpload(createXHR: () => XMLHttpRequest = () => new XMLHttpRequest()): DirectUpload {
  return (ticket, file, signal, onProgress) => new Promise<void>((resolve, reject) => {
    const url = new URL(ticket.uploadUrl);
    if (url.protocol !== "https:" || url.username || url.password || ticket.method !== "PUT") {
      reject(new R2TransferError("The backend returned an invalid upload destination.", 0)); return;
    }
    if (Object.keys(ticket.requiredHeaders).some(name => /^(authorization|cookie|content-length|proxy-authorization)$/i.test(name))) {
      reject(new R2TransferError("The backend returned unsupported upload headers.", 0)); return;
    }
    if (signal.aborted) { reject(new DOMException("Upload cancelled", "AbortError")); return; }
    const xhr = createXHR();
    let settled = false;
    function cleanup() {
      signal.removeEventListener("abort", abort);
      xhr.upload.onprogress = null;
      xhr.onload = xhr.onerror = xhr.onabort = xhr.ontimeout = null;
    }
    function finish(error?: Error) {
      if (settled) return;
      settled = true;
      cleanup();
      if (error) reject(error); else resolve();
    }
    function abort() { xhr.abort(); finish(new DOMException("Upload cancelled", "AbortError")); }
    xhr.onload = () => {
      // A previous immutable PUT can have succeeded even if its response was
      // lost. Both 2xx and 412 must be followed by backend completion/HEAD.
      if ((xhr.status >= 200 && xhr.status < 300) || xhr.status === 412) finish();
      else finish(new R2TransferError("R2 rejected the upload. Check the signed URL, headers and bucket CORS.", xhr.status));
    };
    xhr.onerror = () => finish(new R2TransferError("Upload connection failed. Check your network and the Admin origin in R2 CORS.", 0));
    xhr.ontimeout = () => finish(new R2TransferError("Upload timed out. Retry will first check whether the file reached R2.", 0));
    xhr.onabort = () => finish(new DOMException("Upload cancelled", "AbortError"));
    xhr.upload.onprogress = event => onProgress({ loaded: event.loaded, total: event.lengthComputable ? event.total : file.size });
    signal.addEventListener("abort", abort, { once: true });
    try {
      xhr.open("PUT", ticket.uploadUrl, true);
      xhr.withCredentials = false;
      xhr.timeout = 300_000;
      for (const [name, value] of Object.entries(ticket.requiredHeaders)) xhr.setRequestHeader(name, value);
      xhr.send(file);
    } catch {
      finish(new R2TransferError("The browser could not start this upload.", 0));
    }
  });
}

export const uploadDirect = createDirectUpload();
