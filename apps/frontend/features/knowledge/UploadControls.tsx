"use client";

import { useMemo, useRef, useState, useSyncExternalStore } from "react";
import { UPLOAD_ACCEPT } from "./file-policy";
import { DesignIcon } from "./DesignIcon";
import { useKnowledge } from "./KnowledgeProvider";
import { formatEntryProgress, uploadPercent, uploadStateLabel, type UploadEntry } from "./upload-queue";
import styles from "./knowledge.module.css";

export { formatEntryProgress, uploadPercent, uploadStateLabel };

const emptyEntries: readonly UploadEntry[] = [];

export function useUploadEntries() {
  const { queue } = useKnowledge();
  const entries = useSyncExternalStore(
    listener => queue ? queue.subscribe(listener) : () => {},
    () => queue ? queue.getSnapshot() : emptyEntries,
    () => emptyEntries,
  );
  const summary = useMemo(() => ({
    total: entries.length,
    queued: entries.filter(e => e.state === "queued").length,
    active: entries.filter(e => ["preparing", "uploading", "verifying"].includes(e.state)).length,
    stored: entries.filter(e => e.state === "stored").length,
    failed: entries.filter(e => e.state === "failed").length,
    cancelled: entries.filter(e => e.state === "cancelled").length,
  }), [entries]);
  return { queue, entries, summary };
}

export function UploadDropzone({
  folder,
  variant = "modal",
  disabled = false,
  onErrors,
  onAdded,
}: {
  folder: string;
  variant?: "modal" | "page";
  disabled?: boolean;
  onErrors?: (errors: string[]) => void;
  onAdded?: (count: number) => void;
}) {
  const { queue } = useKnowledge();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);

  function handleFiles(fileList: FileList | null) {
    if (!queue || !fileList?.length || disabled) return;
    const files = Array.from(fileList);
    const errors = queue.add(files, folder);
    onErrors?.(errors);
    const addedCount = Math.max(0, files.length - errors.length);
    if (addedCount > 0) onAdded?.(addedCount);
  }

  return (
    <div
      className={`${styles.dropzone} ${dragging ? styles.dropzoneActive : ""} ${variant === "page" ? styles.dropzoneLarge : ""}`}
      onDragOver={e => { e.preventDefault(); if (!disabled) setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => {
        e.preventDefault();
        setDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={UPLOAD_ACCEPT}
        disabled={disabled}
        className={styles.srOnlyInput}
        aria-label="Choose Markdown, text, or JSON files to upload"
        onChange={e => {
          handleFiles(e.target.files);
          e.currentTarget.value = "";
        }}
      />
      <DesignIcon name={variant === "page" ? "upload-page-CloudUpload" : "upload-modal-CloudUpload"} />
      <p className={styles.dropzoneTitle}>Drag and drop files here, or browse from your computer</p>
      <p className={styles.muted}>Supported by backend: Markdown (.md), Plain text (.txt), JSON (.json) up to 10 MiB per file.</p>
      <button
        type="button"
        disabled={disabled}
        className={styles.browseButton}
        onClick={() => inputRef.current?.click()}
      >
        Choose files
      </button>
    </div>
  );
}
