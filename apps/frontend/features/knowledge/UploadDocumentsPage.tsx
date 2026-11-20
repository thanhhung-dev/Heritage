"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { DesignIcon } from "./DesignIcon";
import { FolderBrowser, KnowledgeTopPath } from "./FolderBrowser";
import { breadcrumbParts, documentHref, libraryHref, uploadHref } from "./folder-state";
import { formatFileSize } from "./file-policy";
import { useKnowledge } from "./KnowledgeProvider";
import { useKnowledgeFolder } from "./useKnowledgeFolder";
import { UploadDropzone, uploadPercent, useUploadEntries } from "./UploadControls";
import type { UploadEntry } from "./upload-queue";
import styles from "./knowledge.module.css";

function destinationLine(root: string, prefix: string): string {
  const parts = breadcrumbParts(root, prefix).map(p => p.label);
  return ["Cloudflare R2", "knowledge-heritage", ...(parts.length ? parts : ["All documents"])].join("   ›   ");
}

function rowTransferHeading(entry: UploadEntry): string {
  switch (entry.state) {
    case "stored": return "Completed";
    case "verifying": return "Verifying upload · 100%";
    case "uploading": return `Uploading · ${uploadPercent(entry)}%`;
    case "preparing": return "Preparing upload…";
    case "failed": return "Failed";
    case "cancelled": return "Cancelled";
    case "queued": return "Ready to upload";
  }
}

function rowTransferSubtext(entry: UploadEntry): string {
  if (entry.state === "stored") {
    return `Stored in R2 · ${entry.object?.key ?? entry.file.name}`;
  }
  if (entry.state === "uploading" || entry.state === "verifying") {
    return `${formatFileSize(entry.loaded)} of ${formatFileSize(entry.total)} transferred`;
  }
  if (entry.state === "failed" || entry.state === "cancelled") {
    return entry.error || "Transfer interrupted · Not stored in R2";
  }
  return `Destination: ${entry.folder || "/"} · Waiting to start`;
}

export function UploadDocumentsPage() {
  const query = useSearchParams();
  const router = useRouter();
  const { root } = useKnowledge();
  const listing = useKnowledgeFolder(query.has("prefix") ? query.get("prefix")! : undefined);
  const { queue, entries, summary } = useUploadEntries();
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const latestStored = entries.filter(e => e.state === "stored" && e.object).at(-1)?.object;

  return (
    <section className={styles.page} aria-label="Upload documents">
      <KnowledgeTopPath prefix={listing.prefix} current="Upload documents" />

      <header className={styles.header}>
        <div>
          <h1>Upload documents</h1>
          <p>Store original files in Cloudflare R2, then complete metadata before submitting for review.</p>
        </div>
        <div className={styles.actions}>
          {summary.queued > 0 && (
            <button
              type="button"
              className={`${styles.figmaBtn} ${styles.figmaBtnPrimary}`}
              disabled={summary.active > 0}
              onClick={() => queue?.start()}
            >
              Upload {summary.queued} queued {summary.queued === 1 ? "file" : "files"}
            </button>
          )}
          <Link href={libraryHref(listing.prefix)} className={styles.figmaBtn}>
            Back to library
          </Link>
        </div>
      </header>

      <div className={styles.contextBar}>
        <span className={styles.contextBadge}>CLOUDFLARE R2</span>
        <span className={styles.contextText}>
          Direct presigned PUT to bucket <code>knowledge-heritage</code> · Prefix: <code>{listing.prefix || "/"}</code> · Allowed formats: .md, .txt, .json
        </span>
      </div>

      <div className={styles.workspace}>
        <FolderBrowser
          prefix={listing.prefix}
          showDestinationNote
          onSelect={prefix => router.push(uploadHref(prefix))}
        />

        <div className={styles.mainColumn} style={{ gap: 20 }}>
          <div className={styles.destinationBreadcrumbBar}>
            <DesignIcon name="upload-page-FolderOpen1" />
            <span className={styles.destinationBreadcrumbText}>
              {destinationLine(root, listing.prefix)}
            </span>
            <Link href={libraryHref(listing.prefix)} className={styles.figmaBtn}>
              Change destination
            </Link>
          </div>

          <UploadDropzone
            folder={listing.prefix}
            variant="page"
            onErrors={errors => setValidationErrors(errors)}
          />

          {validationErrors.length > 0 && (
            <div className={styles.error} role="alert">
              {validationErrors.map((err, index) => <p key={index}>{err}</p>)}
            </div>
          )}

          <div className={styles.uploadSection}>
            <div className={styles.uploadListHeader}>
              <h2>Upload queue</h2>
              <span className={styles.muted}>
                {summary.total} {summary.total === 1 ? "file" : "files"} · {summary.stored} completed · {summary.active} uploading · {summary.failed} failed
              </span>
            </div>

            <div className={styles.queueBox} role="region" aria-label="Upload queue" aria-live="polite">
              <div className={styles.queueTableHeader}>
                <div className={styles.queueColFile}>File</div>
                <div className={styles.queueColStatus}>Upload status</div>
                <div className={styles.queueColAction}>Actions</div>
              </div>

              {entries.length === 0 ? (
                <div className={styles.empty}>
                  <DesignIcon name="upload-page-FileText" />
                  <h2>No files in the upload queue</h2>
                  <p className={styles.muted}>
                    Choose Markdown (.md), TXT (.txt), or JSON (.json) files above, then click Upload to store them in Cloudflare R2.
                  </p>
                </div>
              ) : (
                entries.map(entry => {
                  const ext = entry.file.name.includes(".") ? entry.file.name.split(".").pop()?.toUpperCase() : "FILE";
                  return (
                    <div key={entry.id} className={styles.queueTableRow}>
                      <DesignIcon name="upload-page-FileText" />
                      <div className={`${styles.queueColFile} ${styles.fileIdentityText}`}>
                        <span className={styles.fileIdentityTitle}>{entry.file.name}</span>
                        <span className={styles.fileIdentitySub}>
                          {ext} · {formatFileSize(entry.file.size)}
                        </span>
                      </div>

                      <div className={styles.queueColStatus}>
                        <div
                          className={`${styles.transferStateLine} ${
                            entry.state === "failed" ? styles.transferStateFailed : ""
                          }`}
                        >
                          <DesignIcon
                            name={
                              entry.state === "stored"
                                ? "upload-page-CircleCheck"
                                : entry.state === "failed"
                                ? "upload-page-CircleAlert"
                                : ["preparing", "uploading", "verifying"].includes(entry.state)
                                ? "upload-page-LoaderCircle"
                                : "upload-page-FileText"
                            }
                          />
                          <span>{rowTransferHeading(entry)}</span>
                        </div>
                        <div className={styles.progressTrack}>
                          <div
                            className={styles.progressFill}
                            style={{ width: `${entry.state === "failed" ? 0 : uploadPercent(entry)}%` }}
                          />
                        </div>
                        <span className={styles.muted}>{rowTransferSubtext(entry)}</span>
                      </div>

                      <div className={styles.queueColAction}>
                        {entry.state === "stored" && entry.object && (
                          <Link href={documentHref("metadata", entry.object.key)} className={styles.figmaBtn}>
                            Edit metadata
                          </Link>
                        )}
                        {["preparing", "uploading"].includes(entry.state) && (
                          <button
                            type="button"
                            className={styles.figmaBtn}
                            onClick={() => queue?.cancel(entry.id)}
                          >
                            Cancel upload
                          </button>
                        )}
                        {entry.state === "queued" && (
                          <>
                            <button
                              type="button"
                              className={`${styles.figmaBtn} ${styles.figmaBtnPrimary}`}
                              onClick={() => queue?.start()}
                            >
                              Start upload
                            </button>
                            <button
                              type="button"
                              className={styles.figmaBtn}
                              onClick={() => queue?.remove(entry.id)}
                            >
                              Remove
                            </button>
                          </>
                        )}
                        {["failed", "cancelled"].includes(entry.state) && (
                          <button
                            type="button"
                            className={styles.figmaBtn}
                            onClick={() => queue?.retry(entry.id)}
                          >
                            Retry upload
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <p className={styles.muted}>
              Live R2 transfer states · Verified completion required before an object is marked Stored in R2
            </p>
          </div>

          <div className={styles.uploadNextSteps}>
            <div className={styles.panel}>
              <div className={styles.panelHeading}>
                <h2>Complete metadata for the uploaded file</h2>
                <p>
                  {latestStored
                    ? `${latestStored.name} · Stored in R2`
                    : "Complete an upload above to inspect its metadata screen"}
                </p>
              </div>

              <div className={styles.metaTwoCols}>
                <div className={styles.metaField}>
                  <span className={styles.metaFieldLabel}>Document title</span>
                  <span className={styles.metaFieldValue}>
                    {latestStored ? latestStored.name.replace(/\.[^.]+$/, "") : "—"}
                  </span>
                </div>
                <div className={styles.metaField}>
                  <span className={styles.metaFieldLabel}>Review / ingestion</span>
                  <span className={styles.metaFieldValue}>Unavailable · Not run</span>
                </div>
              </div>

              <div className={styles.replacementHeader}>
                <span className={styles.muted}>
                  Inspect R2 HEAD metadata and editorial fields before review.
                </span>
                {latestStored ? (
                  <Link
                    href={documentHref("metadata", latestStored.key)}
                    className={`${styles.figmaBtn} ${styles.figmaBtnPrimary}`}
                  >
                    Continue to metadata
                  </Link>
                ) : (
                  <button type="button" className={`${styles.figmaBtn} ${styles.figmaBtnPrimary}`} disabled>
                    Continue to metadata
                  </button>
                )}
              </div>
            </div>

            <div className={styles.notice}>
              <DesignIcon name="upload-page-Info" />
              <div className={styles.noticeBody}>
                <span className={styles.noticeTitle}>Upload complete ≠ published</span>
                <p>
                  Completion means stored in R2 only. Submit for review separately. Only an approved revision that is successfully indexed becomes available to the chatbot. Uploading and failed files cannot be submitted.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
