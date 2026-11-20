"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Modal } from "antd";
import { DesignIcon } from "./DesignIcon";
import { breadcrumbParts, documentHref } from "./folder-state";
import { FolderBrowser } from "./FolderBrowser";
import { formatFileSize } from "./file-policy";
import { useKnowledge } from "./KnowledgeProvider";
import { UploadDropzone, uploadPercent, uploadStateLabel, useUploadEntries } from "./UploadControls";
import styles from "./knowledge.module.css";

function destinationBreadcrumbLabel(root: string, prefix: string): string {
  const parts = breadcrumbParts(root, prefix).map(p => p.label);
  return ["knowledge-heritage", ...(parts.length ? parts : ["All documents"])].join("  ›  ");
}

export function UploadDocumentsModal({
  prefix,
  open,
  onClose,
}: {
  prefix: string;
  open: boolean;
  onClose: () => void;
}) {
  const { root } = useKnowledge();
  const { queue, entries } = useUploadEntries();
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [destination, setDestination] = useState(prefix);
  const [choosingFolder, setChoosingFolder] = useState(false);
  useEffect(() => { if (open) { setDestination(prefix); setChoosingFolder(false); setValidationErrors([]); } }, [open, prefix]);
  const folderEntries = entries.filter(entry => entry.folder === destination);
  const activeInFolder = folderEntries.some(entry => ["preparing", "uploading", "verifying"].includes(entry.state));
  const queuedInFolder = folderEntries.filter(entry => entry.state === "queued");
  const latestStored = folderEntries.filter(entry => entry.state === "stored" && entry.object).at(-1)?.object;
  const totalBytes = folderEntries.reduce((sum, entry) => sum + entry.file.size, 0);

  function closeModal() {
    if (activeInFolder) return;
    setValidationErrors([]);
    onClose();
  }

  const queueStatusLabel = activeInFolder
    ? "Uploading to R2…"
    : queuedInFolder.length > 0
    ? "Ready to upload"
    : folderEntries.some(e => e.state === "stored")
    ? "Stored in R2"
    : "Select files";

  return (
    <Modal
      open={open}
      onCancel={closeModal}
      footer={null}
      width={720}
      centered
      styles={{ mask: { backgroundColor: "rgba(32,31,28,.32)" } }}
      closable={!activeInFolder}
      maskClosable={!activeInFolder}
      closeIcon={<DesignIcon name="upload-modal-X" />}
      className={styles.dialog}
      title={
        <div>
          <div style={{ fontSize: 18, lineHeight: "28px", fontWeight: 600, letterSpacing: "-0.45px", color: "#201f1c" }}>
            Upload documents
          </div>
          <p className={styles.dialogDescription}>
            Store original files in Cloudflare R2. Add metadata after uploading.
          </p>
        </div>
      }
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 20, marginTop: 12 }}>
        <div className={styles.destinationSection}>
          <span className={styles.destinationLabel}>Destination</span>
          <div className={styles.destinationBox}>
            <DesignIcon name="upload-modal-FolderOpen" />
            <div>
              <span className={styles.muted}>Cloudflare R2</span>
              <span className={styles.destinationPath}>{destinationBreadcrumbLabel(root, destination)}</span>
            </div>
            <button type="button" disabled={activeInFolder} onClick={() => setChoosingFolder(value => !value)} className={styles.figmaBtn}>
              Change folder
            </button>
          </div>
          {choosingFolder && <div className={styles.folderPicker}>
            <FolderBrowser prefix={destination} onSelect={folder => { setDestination(folder); setChoosingFolder(false); }} />
          </div>}
        </div>

        <UploadDropzone
          folder={destination}
          variant="modal"
          disabled={entries.some(entry => ["preparing", "uploading", "verifying"].includes(entry.state))}
          onErrors={errors => setValidationErrors(errors)}
        />

        {validationErrors.length > 0 && (
          <div className={styles.error} role="alert">
            {validationErrors.map((err, index) => <p key={index}>{err}</p>)}
          </div>
        )}

        {folderEntries.length > 0 && (
          <div className={styles.uploadSection} aria-live="polite">
            <div className={styles.uploadListHeader}>
              <span className={styles.uploadListTitle}>Selected files ({folderEntries.length})</span>
              <span className={styles.muted}>{queueStatusLabel}</span>
            </div>
            <div className={styles.modalFileList}>
              {folderEntries.map(entry => {
                const ext = entry.file.name.includes(".") ? entry.file.name.split(".").pop()?.toUpperCase() : "FILE";
                return (
                  <div key={entry.id} className={styles.modalFileRow}>
                    <DesignIcon name="upload-modal-FileText" />
                    <div className={styles.fileIdentityText}>
                      <span className={styles.fileIdentityTitle}>{entry.file.name}</span>
                      <span className={styles.fileIdentitySub}>
                        {ext} · {formatFileSize(entry.file.size)} · {uploadStateLabel(entry.state)}
                        {["uploading", "verifying"].includes(entry.state) ? ` (${uploadPercent(entry)}%)` : ""}
                      </span>
                      {["uploading", "verifying", "stored"].includes(entry.state) && (
                        <div className={styles.progressTrack} style={{ marginTop: 4 }}>
                          <div className={styles.progressFill} style={{ width: `${uploadPercent(entry)}%` }} />
                        </div>
                      )}
                      {entry.object && (
                        <span className={styles.fileIdentitySub}>
                          Stored key: <code>{entry.object.key}</code>
                        </span>
                      )}
                      {entry.error && <p className={styles.formError} role="alert">{entry.error}</p>}
                    </div>
                    <div className={styles.actions}>
                      {["failed", "cancelled"].includes(entry.state) && (
                        <button type="button" className={styles.figmaBtn} onClick={() => queue?.retry(entry.id)}>
                          Retry
                        </button>
                      )}
                      {["queued", "preparing", "uploading"].includes(entry.state) && entry.state !== "queued" && (
                        <button type="button" className={styles.figmaBtn} onClick={() => queue?.cancel(entry.id)}>
                          Cancel
                        </button>
                      )}
                      {["queued", "stored", "failed", "cancelled"].includes(entry.state) && (
                        <button
                          type="button"
                          className={styles.removeIconBtn}
                          aria-label={`Remove ${entry.file.name} from queue`}
                          onClick={() => queue?.remove(entry.id)}
                        >
                          <DesignIcon name="upload-modal-X1" />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className={styles.notice}>
          <DesignIcon name="upload-modal-Info" />
          <div className={styles.noticeBody}>
            <span className={styles.noticeTitle}>Upload does not publish to the chatbot</span>
            <p>
              Files are stored in Cloudflare R2 only. Review and chatbot indexing are not available yet.
            </p>
          </div>
        </div>

      </div>

      <div className={styles.modalFooterBar}>
        <span className={styles.muted}>
          {folderEntries.length} {folderEntries.length === 1 ? "file" : "files"} · {formatFileSize(totalBytes)} total
        </span>
        <div className={styles.actions}>
          <button type="button" className={styles.figmaBtn} disabled={activeInFolder} onClick={closeModal}>
            {folderEntries.some(e => e.state === "stored") && queuedInFolder.length === 0 ? "Done" : "Cancel"}
          </button>
          {latestStored && !activeInFolder && (
            <Link href={documentHref("metadata", latestStored.key)} onClick={closeModal} className={styles.figmaBtn}>
              Continue to metadata
            </Link>
          )}
          <button
            type="button"
            className={`${styles.figmaBtn} ${styles.figmaBtnPrimary}`}
            disabled={activeInFolder || queuedInFolder.length === 0}
            onClick={() => queue?.start(queuedInFolder.map(entry => entry.id))}
          >
            {activeInFolder
              ? "Uploading…"
              : queuedInFolder.length > 0
              ? `Upload ${queuedInFolder.length} ${queuedInFolder.length === 1 ? "file" : "files"}`
              : "Upload files"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
