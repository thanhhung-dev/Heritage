"use client";

import { useState } from "react";
import Link from "next/link";
import { Button, Modal, Progress } from "antd";
import { DesignIcon } from "./DesignIcon";
import { documentHref, uploadHref } from "./folder-state";
import { formatFileSize } from "./file-policy";
import { UploadDropzone, formatEntryProgress, uploadPercent, uploadStateLabel, useUploadEntries } from "./UploadControls";
import styles from "./knowledge.module.css";

export function UploadDocumentsModal({
  prefix,
  open,
  onClose,
}: {
  prefix: string;
  open: boolean;
  onClose: () => void;
}) {
  const { queue, entries, summary } = useUploadEntries();
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const folderEntries = entries.filter(entry => entry.folder === prefix);
  const activeInFolder = folderEntries.some(entry => ["preparing", "uploading", "verifying"].includes(entry.state));
  const latestStored = folderEntries.filter(entry => entry.state === "stored" && entry.object).at(-1)?.object;

  function closeModal() {
    if (activeInFolder) return;
    setValidationErrors([]);
    onClose();
  }

  return (
    <Modal
      open={open}
      onCancel={closeModal}
      footer={null}
      width={720}
      closable={!activeInFolder}
      maskClosable={!activeInFolder}
      className={styles.dialog}
      title="Upload documents"
    >
      <p className={styles.dialogDescription}>
        Upload original documents to Cloudflare R2. Uploaded files are stored in the bucket and are not automatically indexed or published to the chatbot.
      </p>

      <div className={styles.destinationBox}>
        <DesignIcon name="upload-modal-FolderOpen" />
        <div>
          <span className={styles.muted}>Destination folder (knowledge-heritage)</span>
          <strong className={styles.destinationPath}>{prefix || "/"}</strong>
        </div>
        <Link href={uploadHref(prefix)} onClick={closeModal} className={styles.fullPageLink}>
          Open full upload workspace
        </Link>
      </div>

      <UploadDropzone
        folder={prefix}
        variant="modal"
        onErrors={errors => setValidationErrors(errors)}
      />

      {validationErrors.length > 0 && (
        <div className={styles.error} role="alert">
          {validationErrors.map((err, index) => <p key={index}>{err}</p>)}
        </div>
      )}

      {folderEntries.length > 0 && (
        <div className={styles.uploadList} aria-live="polite">
          <div className={styles.uploadListHeader}>
            <strong>Selected files ({folderEntries.length})</strong>
            <span className={styles.muted}>
              {summary.stored} stored · {summary.failed} failed · {summary.active} in progress
            </span>
          </div>
          {folderEntries.map(entry => (
            <div key={entry.id} className={styles.uploadRow}>
              <div className={styles.uploadFileMeta}>
                <DesignIcon name="upload-modal-FileText" />
                <div>
                  <div className={styles.uploadFileName}>{entry.file.name}</div>
                  <p className={styles.muted}>
                    {formatFileSize(entry.file.size)} · {entry.contentType} · {uploadStateLabel(entry.state)}
                  </p>
                  {["uploading", "verifying", "stored"].includes(entry.state) && (
                    <>
                      <Progress
                        percent={uploadPercent(entry)}
                        size="small"
                        showInfo={false}
                        status={entry.state === "failed" ? "exception" : entry.state === "stored" ? "success" : "active"}
                        aria-label={`Upload progress for ${entry.file.name}`}
                      />
                      <p className={styles.muted}>{formatEntryProgress(entry)}</p>
                    </>
                  )}
                  {entry.object && (
                    <p className={styles.storedKey}>Stored key: <code>{entry.object.key}</code></p>
                  )}
                  {entry.error && <p className={styles.formError} role="alert">{entry.error}</p>}
                </div>
              </div>
              <div className={styles.rowActions}>
                {["failed", "cancelled"].includes(entry.state) && (
                  <Button size="small" onClick={() => queue?.retry(entry.id)}>Retry</Button>
                )}
                {["queued", "preparing", "uploading"].includes(entry.state) && (
                  <Button size="small" onClick={() => queue?.cancel(entry.id)}>Cancel</Button>
                )}
                {["queued", "stored", "failed", "cancelled"].includes(entry.state) && (
                  <Button
                    type="text"
                    size="small"
                    aria-label={`Remove ${entry.file.name} from queue`}
                    onClick={() => queue?.remove(entry.id)}
                  >
                    <DesignIcon name="upload-modal-X1" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className={styles.notice}>
        <DesignIcon name="upload-modal-Info" />
        <p>
          100% file transfer is verified by the backend before an object is marked <strong>Stored in R2</strong>. Review and RAG ingestion remain separate steps.
        </p>
      </div>

      <div className={styles.dialogFooter}>
        <Button disabled={activeInFolder} onClick={closeModal}>
          {folderEntries.some(e => e.state === "stored") ? "Done" : "Cancel"}
        </Button>
        {latestStored && (
          <Link href={documentHref("metadata", latestStored.key)} onClick={closeModal}>
            <Button>Continue to metadata</Button>
          </Link>
        )}
        <Button
          type="primary"
          loading={activeInFolder}
          disabled={!folderEntries.some(entry => entry.state === "queued")}
          onClick={() => queue?.start()}
        >
          Upload to R2
        </Button>
      </div>
    </Modal>
  );
}
