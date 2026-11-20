import { ApiError } from "../../lib/api";
import { knowledgeError } from "../../services/knowledge.service";
import { uploadFileType } from "./file-policy";
import { R2TransferError, type DirectUpload } from "./upload-transport";
import type { KnowledgeApi, KnowledgeCompletion, KnowledgeObject, KnowledgeUploadTicket } from "./types";

export type UploadState = "queued" | "preparing" | "uploading" | "verifying" | "stored" | "failed" | "cancelled";
export interface UploadEntry {
  id: string;
  file: File;
  folder: string;
  contentType: string;
  state: UploadState;
  loaded: number;
  total: number;
  error?: string;
  object?: KnowledgeObject;
}
interface SignedTransfer { ticket: KnowledgeUploadTicket; urlExpiresAt: number }
interface QueueOptions { concurrency?: number; now?: () => number; id?: () => string; onStored?: (object: KnowledgeObject) => void }

/** Shared by modal/page. Signed URLs live only in private, transient memory. */
export class KnowledgeUploadQueue {
  private entries: readonly UploadEntry[] = [];
  private listeners = new Set<() => void>();
  private transfers = new Map<string, SignedTransfer>();
  private active = new Map<string, AbortController>();
  private started = false;
  private disposed = false;
  private readonly concurrency: number;

  constructor(private api: KnowledgeApi, private directUpload: DirectUpload, private options: QueueOptions = {}) {
    this.concurrency = Math.max(1, Math.min(options.concurrency ?? 2, 3));
  }
  getSnapshot = (): readonly UploadEntry[] => this.entries;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  private emit() { if (!this.disposed) for (const listener of this.listeners) listener(); }
  private update(id: string, changes: Partial<UploadEntry>) {
    if (this.disposed) return;
    this.entries = this.entries.map(entry => entry.id === id ? { ...entry, ...changes } : entry);
    this.emit();
  }
  add(files: readonly File[], folder: string): string[] {
    if (this.disposed) return [];
    const errors: string[] = [];
    const added: UploadEntry[] = [];
    for (const file of files) {
      try {
        const contentType = uploadFileType(file);
        // Repeated clicks/selections must not create duplicate active sessions.
        if ([...this.entries, ...added].some(entry => entry.folder === folder && entry.file.name === file.name
            && !["cancelled", "failed"].includes(entry.state))) {
          errors.push(`${file.name}: already in this upload queue.`); continue;
        }
        added.push({ id: this.options.id?.() ?? crypto.randomUUID(), file, folder, contentType,
          state: "queued", loaded: 0, total: file.size });
      } catch (error) { errors.push(`${file.name}: ${error instanceof Error ? error.message : "Invalid file."}`); }
    }
    if (added.length) { this.entries = [...this.entries, ...added]; this.emit(); if (this.started) this.pump(); }
    return errors;
  }
  start() { if (!this.disposed) { this.started = true; this.pump(); } }
  retry(id: string) {
    if (this.active.has(id) || !this.entries.some(entry => entry.id === id && ["failed", "cancelled"].includes(entry.state))) return;
    this.update(id, { state: "queued", error: undefined });
    this.start();
  }
  cancel(id: string): boolean {
    const entry = this.entries.find(row => row.id === id);
    if (!entry || !["queued", "preparing", "uploading"].includes(entry.state)) return false;
    this.update(id, { state: "cancelled", error: "Cancelled. A retry checks the existing session before uploading again." });
    this.active.get(id)?.abort();
    return true;
  }
  remove(id: string) {
    if (this.active.has(id)) return;
    this.entries = this.entries.filter(entry => entry.id !== id);
    this.transfers.delete(id);
    this.emit();
  }
  private pump() {
    if (this.disposed || !this.started) return;
    while (this.active.size < this.concurrency) {
      const entry = this.entries.find(row => row.state === "queued" && !this.active.has(row.id));
      if (!entry) break;
      const controller = new AbortController();
      this.active.set(entry.id, controller);
      void this.run(entry, controller).finally(() => {
        this.active.delete(entry.id);
        if (!this.active.size && !this.entries.some(row => row.state === "queued")) this.started = false;
        this.pump();
      });
    }
  }
  private stored(entry: UploadEntry, transfer: SignedTransfer, result: KnowledgeCompletion) {
    if (result.status !== "stored" || result.uploadId !== transfer.ticket.uploadId
        || result.object?.bucket !== "knowledge-heritage" || result.object.key !== transfer.ticket.objectKey) {
      throw new ApiError("The backend returned an unexpected completion result.", 503);
    }
    this.transfers.delete(entry.id);
    this.update(entry.id, { state: "stored", loaded: entry.file.size, error: undefined, object: result.object });
    if (!this.disposed) this.options.onStored?.(result.object);
  }
  private async run(entry: UploadEntry, controller: AbortController) {
    const signal = controller.signal;
    try {
      let transfer = this.transfers.get(entry.id);
      if (transfer) {
        this.update(entry.id, { state: "verifying", error: undefined });
        try {
          const result = await this.api.complete(transfer.ticket.uploadId, signal);
          this.stored(entry, transfer, result); return;
        } catch (error) {
          if (error instanceof ApiError && error.status === 410) {
            this.transfers.delete(entry.id); transfer = undefined;
          } else if (!(error instanceof ApiError && error.status === 404)) throw error;
        }
        if (transfer && (this.options.now?.() ?? Date.now()) >= transfer.urlExpiresAt) {
          throw new ApiError("The PUT URL expired before the file was stored. Retry after this session expires at "
            + transfer.ticket.sessionExpiresAt + ".", 409);
        }
      }
      if (!transfer) {
        this.update(entry.id, { state: "preparing", error: undefined, loaded: 0 });
        const ticket = await this.api.beginUpload({ folder: entry.folder, filename: entry.file.name,
          contentType: entry.contentType, size: entry.file.size }, signal);
        transfer = { ticket, urlExpiresAt: (this.options.now?.() ?? Date.now()) + ticket.expiresIn * 1000 - 5000 };
        this.transfers.set(entry.id, transfer);
      }
      if (signal.aborted) throw new DOMException("Upload cancelled", "AbortError");
      this.update(entry.id, { state: "uploading", error: undefined, loaded: 0 });
      await this.directUpload(transfer.ticket, entry.file, signal, progress => {
        if (!signal.aborted) this.update(entry.id, { loaded: Math.min(progress.loaded, entry.file.size), total: progress.total });
      });
      if (signal.aborted) throw new DOMException("Upload cancelled", "AbortError");
      this.update(entry.id, { state: "verifying", loaded: entry.file.size });
      const result = await this.api.complete(transfer.ticket.uploadId, signal);
      this.stored(entry, transfer, result);
    } catch (error) {
      this.update(entry.id, { state: signal.aborted ? "cancelled" : "failed",
        error: signal.aborted ? "Cancelled. Retry checks the existing upload session first."
          : error instanceof R2TransferError ? error.message : knowledgeError(error) });
    }
  }
  dispose() {
    this.disposed = true;
    for (const [id, controller] of this.active) {
      // A complete request may already have published on the backend. Never
      // describe it as cancelled; next listing/complete establishes the result.
      if (this.entries.find(row => row.id === id)?.state !== "verifying") controller.abort();
    }
    this.listeners.clear();
    this.transfers.clear();
  }
}
