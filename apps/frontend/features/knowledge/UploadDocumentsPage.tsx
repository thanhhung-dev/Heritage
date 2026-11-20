"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button, Progress } from "antd";
import { DesignIcon } from "./DesignIcon";
import { FolderBrowser, KnowledgeBreadcrumbs } from "./FolderBrowser";
import { documentHref, libraryHref, uploadHref } from "./folder-state";
import { formatFileSize } from "./file-policy";
import { useKnowledgeFolder } from "./useKnowledgeFolder";
import { UploadDropzone, formatEntryProgress, uploadPercent, uploadStateLabel, useUploadEntries } from "./UploadControls";
import styles from "./knowledge.module.css";

export function UploadDocumentsPage() {
  const query = useSearchParams();
  const router = useRouter();
  const listing = useKnowledgeFolder(query.has("prefix") ? query.get("prefix")! : undefined);
  const { queue, entries, summary } = useUploadEntries();
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const latestStored = entries.filter(e => e.state === "stored" && e.object).at(-1)?.object;

  return (
    <section className={styles.page} aria-label="Upload documents">
      <header className={styles.header}>
        <div>
          <h1>Upload documents</h1>
          <p>Select a destination folder in knowledge-heritage, queue multiple files, and verify storage completion in Cloudflare R2.</p>
        </div>
        <div className={styles.actions}>
          <Link href={libraryHref(listing.prefix)}>
            <Button icon={<DesignIcon name="library-ArrowLeft" />}>Back to library</Button>
          </Link>
          {latestStored && (
            <Link href={documentHref("metadata", latestStored.key)}>
              <Button>Continue to metadata</Button>
            </Link>
          )}
          <Button
            type="primary"
            loading={summary.active > 0}
            disabled={summary.queued === 0}
            onClick={() => queue?.start()}
          >
            Start upload ({summary.queued})
          </Button>
        </div>
      </header>

      <div className={styles.workspace}>
        <FolderBrowser prefix={listing.prefix} onSelect={prefix => router.push(uploadHref(prefix))} />

        <div className={styles.mainColumn}>
          <KnowledgeBreadcrumbs prefix={listing.prefix} current="Upload documents" />

          <div className={styles.destinationBox}>
            <DesignIcon name="upload-page-FolderOpen1" />
            <div>
              <span className={styles.muted}>Selected upload destination (preserved per queued file)</span>
              <strong className={styles.destinationPath}>knowledge-heritage / {listing.prefix || ""}</strong>
            </div>
            <span className={styles.badges}>Storage only · No auto-indexing</span>
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

          <div className={styles.panel}>
            <div className={styles.replacementHeader}>
              <div>
                <h2>Upload queue</h2>
                <p className={styles.muted}>
                  {summary.total} total · {summary.stored} stored in R2 · {summary.active} active · {summary.queued} queued · {summary.failed} failed · {summary.cancelled} cancelled
                </p>
              </div>
              <div className={styles.actions}>
                <Button
                  disabled={summary.queued === 0}
                  type="primary"
                  onClick={() => queue?.start()}
                >
                  Upload queued files
                </Button>
              </div>
            </div>

            {entries.length === 0 ? (
              <div className={styles.empty}>
                <DesignIcon name="upload-page-FileText" />
                <h2>No files in the upload queue</h2>
                <p>Add Markdown (.md), Plain text (.txt), or JSON (.json) files above to prepare a presigned R2 transfer.</p>
              </div>
            ) : (
              <div className={styles.uploadQueueTable} role="region" aria-label="Queued uploads" aria-live="polite">
                {entries.map(entry => (
                  <div key={entry.id} className={styles.uploadRow}>
                    <div className={styles.uploadFileMeta}>
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
                      <div>
                        <div className={styles.uploadFileName}>{entry.file.name}</div>
                        <p className={styles.muted}>
                          Destination: <code>{entry.folder || "/"}</code> · {formatFileSize(entry.file.size)} · {entry.contentType}
                        </p>
                        <Progress
                          percent={uploadPercent(entry)}
                          size="small"
                          showInfo={false}
                          status={entry.state === "failed" ? "exception" : entry.state === "stored" ? "success" : "active"}
                          aria-label={`Progress for ${entry.file.name}`}
                        />
                        <p className={styles.muted}>
                          <strong>{uploadStateLabel(entry.state)}</strong> · {formatEntryProgress(entry)}
                        </p>
                        {entry.object && (
                          <p className={styles.storedKey}>
                            Verified R2 key: <code>{entry.object.key}</code> ·{" "}
                            <Link href={documentHref("details", entry.object.key)}>View details</Link> ·{" "}
                            <Link href={documentHref("metadata", entry.object.key)}>Inspect metadata</Link>
                          </p>
                        )}
                        {entry.error && <p className={styles.formError} role="alert">{entry.error}</p>}
                      </div>
                    </div>
                    <div className={styles.rowActions}>
                      {["failed", "cancelled"].includes(entry.state) && (
                        <Button size="small" onClick={() => queue?.retry(entry.id)}>Retry upload</Button>
                      )}
                      {["queued", "preparing", "uploading"].includes(entry.state) && (
                        <Button size="small" onClick={() => queue?.cancel(entry.id)}>Cancel</Button>
                      )}
                      {["queued", "stored", "failed", "cancelled"].includes(entry.state) && (
                        <Button size="small" type="text" onClick={() => queue?.remove(entry.id)}>
                          Remove
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className={styles.twoColumns}>
            <div className={styles.panel}>
              <h2>Continue to document metadata</h2>
              <p className={styles.muted}>
                After a file reaches <strong>Stored in R2</strong>, you can inspect its storage metadata and the editorial metadata screen. Editorial draft persistence and review submission remain disabled until backend endpoints are added.
              </p>
              <div className={styles.actions} style={{ marginTop: 12 }}>
                {latestStored ? (
                  <Link href={documentHref("metadata", latestStored.key)}>
                    <Button type="primary">Open metadata for {latestStored.name}</Button>
                  </Link>
                ) : (
                  <Button disabled>Complete an upload to inspect metadata</Button>
                )}
              </div>
            </div>
            <div className={styles.panel}>
              <h2>Storage boundary & safety</h2>
              <p className={styles.muted}>
                Files are uploaded directly to Cloudflare R2 using short-lived presigned PUT URLs without exposing your Admin JWT. Completion verifies the staged object before publishing it to the destination folder.
              </p>
            </div>
          </div>

          <div className={styles.notice}>
            <DesignIcon name="upload-page-Info" />
            <p>
              Uploading stores the raw file in <code>knowledge-heritage</code> only. It does not mark the document as reviewed, chunked, embedded, or available to the AI chatbot.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
