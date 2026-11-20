/** Mirrors the mounted /api/admin/knowledge DTOs, independently of review/RAG. */
export interface KnowledgeFolder { name: string; prefix: string }
export interface KnowledgeFile { name: string; key: string; size: number; lastModified: string }
export interface KnowledgePage {
  bucket: "knowledge-heritage";
  prefix: string;
  folders: KnowledgeFolder[];
  files: KnowledgeFile[];
  nextContinuationToken: string | null;
}
export interface KnowledgeObject extends KnowledgeFile {
  bucket: "knowledge-heritage";
  contentType: string;
  etag: string;
  metadata: Record<string, string>;
}
export interface KnowledgeUploadRequest { folder: string; filename: string; contentType: string; size: number }
export interface KnowledgeUploadTicket {
  uploadId: string;
  objectKey: string;
  uploadUrl: string;
  method: "PUT";
  expiresIn: number;
  sessionExpiresAt: string;
  requiredHeaders: Record<string, string>;
}
export interface KnowledgeCompletion { uploadId: string; status: "stored"; object: KnowledgeObject }
export interface KnowledgeDownload { key: string; downloadUrl: string; expiresIn: number }
export interface KnowledgePreview { key: string; content: string; contentType: "text/plain; charset=utf-8"; size: number; etag: string }

export interface KnowledgeApi {
  list(options?: { prefix?: string; continuationToken?: string; limit?: number; signal?: AbortSignal }): Promise<KnowledgePage>;
  object(key: string, signal?: AbortSignal): Promise<KnowledgeObject>;
  preview(key: string, signal?: AbortSignal): Promise<KnowledgePreview>;
  beginUpload(data: KnowledgeUploadRequest, signal?: AbortSignal): Promise<KnowledgeUploadTicket>;
  complete(uploadId: string, signal?: AbortSignal): Promise<KnowledgeCompletion>;
  download(key: string, signal?: AbortSignal): Promise<KnowledgeDownload>;
  createFolder(parentPrefix: string, folderName: string, signal?: AbortSignal): Promise<KnowledgeFolder>;
  deleteObject(key: string, signal?: AbortSignal): Promise<void>;
}
