import { ApiError } from "../../lib/api";
import type { KnowledgeCompletion, KnowledgeDownload, KnowledgeFile, KnowledgeFolder, KnowledgeObject,
  KnowledgePreview, KnowledgeUploadRequest, KnowledgeUploadTicket } from "./types";

function record(value: unknown): value is Record<string, unknown> { return typeof value === "object" && value !== null && !Array.isArray(value); }
function size(value: unknown): value is number { return typeof value === "number" && Number.isSafeInteger(value) && value >= 0; }
function timestamp(value: unknown): value is string { return typeof value === "string" && Number.isFinite(Date.parse(value)); }
function fail(): never { throw new ApiError("The backend returned an unexpected knowledge response. Refresh and try again.", 503); }
function secureUrl(value: unknown): value is string {
  if (typeof value !== "string") return false;
  try { const url = new URL(value); return url.protocol === "https:" && !url.username && !url.password; } catch { return false; }
}

export function isKnowledgeFile(value: unknown): value is KnowledgeFile {
  return record(value) && typeof value.key === "string" && value.key.length > 0
    && typeof value.name === "string" && value.name.length > 0 && size(value.size) && timestamp(value.lastModified);
}

export function checkedObject(value: KnowledgeObject, key?: string): KnowledgeObject {
  if (!isKnowledgeFile(value) || value.bucket !== "knowledge-heritage" || (key !== undefined && value.key !== key)
      || typeof value.contentType !== "string" || typeof value.etag !== "string" || !value.etag
      || !record(value.metadata) || !Object.values(value.metadata).every(item => typeof item === "string")) fail();
  return value;
}

export function checkedPreview(value: KnowledgePreview, key: string): KnowledgePreview {
  if (!record(value) || value.key !== key || value.contentType !== "text/plain; charset=utf-8"
      || typeof value.content !== "string" || !size(value.size) || typeof value.etag !== "string"
      || new TextEncoder().encode(value.content).length !== value.size) fail();
  return value;
}

export function checkedTicket(value: KnowledgeUploadTicket, request: KnowledgeUploadRequest): KnowledgeUploadTicket {
  if (!record(value) || typeof value.uploadId !== "string" || !value.uploadId
      || value.objectKey !== request.folder + request.filename || value.method !== "PUT"
      || !secureUrl(value.uploadUrl) || typeof value.expiresIn !== "number" || !Number.isFinite(value.expiresIn)
      || value.expiresIn <= 0 || value.expiresIn > 900 || !timestamp(value.sessionExpiresAt)
      || !record(value.requiredHeaders) || !Object.values(value.requiredHeaders).every(item => typeof item === "string")) fail();
  const headers = new Headers(value.requiredHeaders);
  if (headers.get("Content-Type") !== request.contentType || headers.get("If-None-Match") !== "*"
      || headers.get("x-amz-meta-upload-id") !== value.uploadId
      || ["Authorization", "Cookie", "Content-Length", "Proxy-Authorization"].some(name => headers.has(name))) fail();
  return value;
}

export function checkedCompletion(value: KnowledgeCompletion, uploadId: string): KnowledgeCompletion {
  if (!record(value) || value.uploadId !== uploadId || value.status !== "stored") fail();
  checkedObject(value.object);
  return value;
}

export function checkedDownload(value: KnowledgeDownload, key: string): KnowledgeDownload {
  if (!record(value) || value.key !== key || !secureUrl(value.downloadUrl) || typeof value.expiresIn !== "number"
      || !Number.isFinite(value.expiresIn) || value.expiresIn <= 0 || value.expiresIn > 900) fail();
  return value;
}

export function checkedFolder(value: KnowledgeFolder, parent: string, name: string): KnowledgeFolder {
  if (!record(value) || value.prefix !== parent + name + "/" || value.name !== name) fail();
  return value;
}
