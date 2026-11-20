"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { App, Tooltip } from "antd";
import { ApiError } from "../../lib/api";
import { isAborted, knowledgeApi, knowledgeError } from "../../services/knowledge.service";
import { DesignIcon } from "./DesignIcon";
import { DeleteFileDialog } from "./FileDialogs";
import { KnowledgeTopPath } from "./FolderBrowser";
import { breadcrumbParts, documentHref, libraryHref } from "./folder-state";
import { formatFileSize } from "./file-policy";
import { downloadKnowledgeFile } from "./knowledge-actions";
import { KnowledgeFeedback } from "./KnowledgeFeedback";
import { useKnowledge } from "./KnowledgeProvider";
import type { KnowledgeObject, KnowledgePreview } from "./types";
import styles from "./knowledge.module.css";

function parentFolderPrefix(root: string, key: string): string {
  const slashIndex = key.lastIndexOf("/");
  if (slashIndex === -1) return root;
  const candidate = key.slice(0, slashIndex + 1);
  return candidate.startsWith(root) ? candidate : root;
}

const PREVIEW_PAGE_CHARS = 1800;

export function DocumentDetails() {
  const query = useSearchParams();
  const router = useRouter();
  const { message } = App.useApp();
  const { root } = useKnowledge();
  const key = query.get("key") ?? "";

  const [object, setObject] = useState<KnowledgeObject | null>(null);
  const [objectLoading, setObjectLoading] = useState(true);
  const [objectError, setObjectError] = useState<unknown>();

  const [preview, setPreview] = useState<KnowledgePreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(true);
  const [previewError, setPreviewError] = useState<unknown>();
  const [previewPage, setPreviewPage] = useState(1);

  const [attempt, setAttempt] = useState(0);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    setPreviewPage(1);
    if (!key) {
      setObject(null);
      setObjectLoading(false);
      setObjectError(new ApiError("Select a document key to inspect details.", 422));
      setPreview(null);
      setPreviewLoading(false);
      return;
    }
    const controller = new AbortController();
    setObjectLoading(true);
    setObjectError(undefined);
    setPreviewLoading(true);
    setPreviewError(undefined);
    setPreview(null);

    void knowledgeApi.object(key, controller.signal)
      .then(result => {
        if (!controller.signal.aborted) {
          setObject(result);
          setObjectLoading(false);
        }
      })
      .catch(err => {
        if (!isAborted(err) && !controller.signal.aborted) {
          setObject(null);
          setObjectError(err);
          setObjectLoading(false);
        }
      });

    void knowledgeApi.preview(key, controller.signal)
      .then(result => {
        if (!controller.signal.aborted) {
          setPreview(result);
          setPreviewLoading(false);
        }
      })
      .catch(err => {
        if (!isAborted(err) && !controller.signal.aborted) {
          setPreview(null);
          setPreviewError(err);
          setPreviewLoading(false);
        }
      });

    return () => controller.abort();
  }, [key, attempt]);

  const folderPrefix = parentFolderPrefix(root, key);
  const folderParts = breadcrumbParts(root, folderPrefix);
  const folderLabel = folderParts.length ? folderParts.map(p => p.label).join(" / ") : "All documents";
  const previewStatus = previewError instanceof ApiError ? previewError.status : undefined;
  const ext = object?.name.includes(".") ? object.name.split(".").pop()?.toUpperCase() : "FILE";

  const previewPages = useMemo(() => {
    if (!preview) return [];
    const text = preview.content;
    if (!text.length) return [""];
    const pages: string[] = [];
    for (let i = 0; i < text.length; i += PREVIEW_PAGE_CHARS) {
      pages.push(text.slice(i, i + PREVIEW_PAGE_CHARS));
    }
    return pages;
  }, [preview]);

  const totalPreviewPages = Math.max(1, previewPages.length);
  const shownPreviewPage = Math.min(previewPage, totalPreviewPages);

  async function handleDownload() {
    if (!key) return;
    try {
      await downloadKnowledgeFile(key);
    } catch (e) {
      void message.error(knowledgeError(e));
    }
  }

  return (
    <section className={styles.page} aria-label="Document details">
      <KnowledgeTopPath
        prefix={folderPrefix}
        current={object?.name || key || "Document details"}
      />

      <header className={styles.header}>
        <div>
          <h1>Document details</h1>
          <p>
            {object
              ? `${object.name} · Stored in R2 · ${folderLabel}`
              : key || "Inspect Cloudflare R2 object details"}
          </p>
        </div>
        <div className={styles.actions}>
          {object && (
            <>
              <button type="button" className={styles.figmaBtn} onClick={() => void handleDownload()}>
                View original
              </button>
              <button type="button" className={styles.figmaBtn} onClick={() => void handleDownload()}>
                Download file
              </button>
              <Tooltip title="Versioned replacement is not supported by the current R2 backend contract.">
                <button type="button" className={styles.figmaBtn} disabled>
                  Replace file
                </button>
              </Tooltip>
              <Link href={documentHref("metadata", object.key)} className={styles.figmaBtn}>
                Edit metadata
              </Link>
              <button
                type="button"
                className={`${styles.figmaBtn} ${styles.figmaBtnDanger}`}
                onClick={() => setDeleting(true)}
              >
                Delete file
              </button>
            </>
          )}
        </div>
      </header>

      <div className={styles.contextBar}>
        <span className={styles.contextBadge}>CLOUDFLARE R2</span>
        <span className={styles.contextText}>
          Live object HEAD & safe UTF-8 text preview from bucket <code>knowledge-heritage</code> · Review and ingestion states are separate from R2 storage
        </span>
      </div>

      {objectLoading ? (
        <KnowledgeFeedback loading />
      ) : objectError || !object ? (
        <KnowledgeFeedback error={objectError} retry={() => setAttempt(n => n + 1)} />
      ) : (
        <>
          <div className={styles.stateCards}>
            <div className={styles.stateCard}>
              <div className={styles.stateTitle}>
                <span className={styles.stateLabel}>Storage</span>
                <span className={styles.badges}>Stored in R2</span>
              </div>
              <p className={styles.stateSummary}>Original file is stored and available to download.</p>
            </div>
            <div className={styles.stateCard}>
              <div className={styles.stateTitle}>
                <span className={styles.stateLabel}>Review</span>
                <span className={styles.badges}>Unavailable</span>
              </div>
              <p className={styles.stateSummary}>No editorial review status returned by the R2 backend.</p>
            </div>
            <div className={styles.stateCard}>
              <div className={styles.stateTitle}>
                <span className={styles.stateLabel}>Ingestion</span>
                <span className={styles.badges}>Unavailable</span>
              </div>
              <p className={styles.stateSummary}>Ingestion and chatbot availability are not reported.</p>
            </div>
          </div>

          <div className={styles.twoColumns}>
            <div className={styles.mainColumn} style={{ gap: 20 }}>
              <div className={styles.panel}>
                <div className={styles.replacementHeader}>
                  <div className={styles.panelHeading} style={{ flex: 1 }}>
                    <h2>Extracted text</h2>
                    <p className={styles.muted}>
                      {preview
                        ? `${preview.content.length.toLocaleString()} characters · ${totalPreviewPages} ${totalPreviewPages === 1 ? "page" : "pages"} · Raw UTF-8 preview from R2`
                        : "Raw UTF-8 text preview from R2"}
                    </p>
                  </div>
                  {preview && (
                    <div className={styles.actions}>
                      <span className={styles.muted}>
                        Page {shownPreviewPage} of {totalPreviewPages}
                      </span>
                      <button
                        type="button"
                        className={styles.figmaBtn}
                        disabled={shownPreviewPage <= 1}
                        onClick={() => setPreviewPage(p => p - 1)}
                      >
                        Previous
                      </button>
                      <button
                        type="button"
                        className={styles.figmaBtn}
                        disabled={shownPreviewPage >= totalPreviewPages}
                        onClick={() => setPreviewPage(p => p + 1)}
                      >
                        Next
                      </button>
                    </div>
                  )}
                </div>

                {previewLoading ? (
                  <KnowledgeFeedback loading />
                ) : preview ? (
                  <div className={styles.previewContainer}>
                    <pre className={styles.previewPre} aria-label="Raw UTF-8 text preview">
                      {previewPages[shownPreviewPage - 1] || "(Empty file)"}
                    </pre>
                    <p className={styles.muted}>
                      Rendered safely as plain text without executing HTML or Markdown · Source key: {object.key} · Page {shownPreviewPage}.
                    </p>
                  </div>
                ) : (
                  <div className={styles.error} role="alert">
                    <strong>
                      {previewStatus === 413
                        ? "File exceeds the 128 KiB preview size limit (HTTP 413)"
                        : previewStatus === 404
                        ? "Object not found for preview (HTTP 404)"
                        : previewStatus === 415 || previewStatus === 422
                        ? "Preview not supported for this content"
                        : "Preview unavailable"}
                    </strong>
                    <p>{knowledgeError(previewError)}</p>
                    <button type="button" className={styles.figmaBtn} onClick={() => void handleDownload()}>
                      Download file instead
                    </button>
                  </div>
                )}
              </div>

              <div className={styles.panel}>
                <div className={styles.panelHeading}>
                  <h2>Chunks</h2>
                  <p>Chunk information is not available for this file.</p>
                </div>

                <div className={styles.figmaTable} role="table" aria-label="Chunks">
                  <div className={styles.figmaTableHeader} role="row">
                    <div className={styles.chunkColId} role="columnheader">Chunk</div>
                    <div className={styles.chunkColPage} role="columnheader">Page</div>
                    <div className={styles.chunkColPreview} role="columnheader">Content preview</div>
                    <div className={styles.chunkColTokens} role="columnheader">Tokens</div>
                    <div className={styles.chunkColAction} role="columnheader" />
                  </div>
                  <div className={styles.empty} style={{ padding: "28px 16px" }}>
                    <p className={styles.muted}>
                      This library does not currently provide chunk previews.
                    </p>
                  </div>
                </div>

                <div className={styles.pagination}>
                  <span className={styles.muted}>Chunk count unavailable</span>
                  <button type="button" className={styles.figmaBtn} disabled>
                    View all chunks
                  </button>
                </div>
              </div>
            </div>

            <div className={styles.mainColumn} style={{ gap: 16 }}>
              <div className={styles.panel}>
                <div className={styles.panelHeading}>
                  <h2>Metadata and original file</h2>
                </div>

                <div className={styles.metaStack}>
                  <div className={styles.metaField}>
                    <span className={styles.metaFieldLabel}>Title</span>
                    <span className={styles.metaFieldValue}>{object.name.replace(/\.[^.]+$/, "")}</span>
                  </div>

                  <div className={styles.metaTwoCols}>
                    <div className={styles.metaField}>
                      <span className={styles.metaFieldLabel}>Region</span>
                      <span className={styles.metaFieldValue}>
                        {object.metadata?.["region"] || "Not provided"}
                      </span>
                    </div>
                    <div className={styles.metaField}>
                      <span className={styles.metaFieldLabel}>Document type</span>
                      <span className={styles.metaFieldValue}>
                        {object.metadata?.["document-type"] || "Not provided"}
                      </span>
                    </div>
                  </div>

                  <div className={styles.metaField}>
                    <span className={styles.metaFieldLabel}>Citation source URL</span>
                    <span className={styles.metaFieldValue}>Not provided by backend</span>
                  </div>

                  <div className={styles.dividerTop}>
                    <div className={styles.metaField}>
                      <span className={styles.metaFieldLabel}>Original file name</span>
                      <span className={styles.metaFieldValue}>{object.name}</span>
                    </div>

                    <div className={styles.metaTwoCols}>
                      <div className={styles.metaField}>
                        <span className={styles.metaFieldLabel}>Format</span>
                        <span className={styles.metaFieldValue}>{ext}</span>
                      </div>
                      <div className={styles.metaField}>
                        <span className={styles.metaFieldLabel}>Size</span>
                        <span className={styles.metaFieldValue}>{formatFileSize(object.size)}</span>
                      </div>
                    </div>

                    <div className={styles.metaField}>
                      <span className={styles.metaFieldLabel}>R2 object key</span>
                      <span className={styles.metaFieldValue}>{object.key}</span>
                    </div>

                    <div className={styles.metaTwoCols}>
                      <div className={styles.metaField}>
                        <span className={styles.metaFieldLabel}>Uploaded by</span>
                        <span className={styles.metaFieldValue}>Not provided by R2 HEAD</span>
                      </div>
                      <div className={styles.metaField}>
                        <span className={styles.metaFieldLabel}>Updated (UTC)</span>
                        <span className={styles.metaFieldValue}>
                          {new Date(object.lastModified).toLocaleString("en-GB", {
                            timeZone: "UTC",
                            dateStyle: "medium",
                            timeStyle: "short",
                          })}
                        </span>
                      </div>
                    </div>

                    <div className={styles.metaField}>
                      <span className={styles.metaFieldLabel}>ETag</span>
                      <span className={styles.metaFieldValue}>{object.etag || "—"}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className={styles.panel}>
                <div className={styles.panelHeading}>
                  <h2>Ingestion status & retry</h2>
                  <p>Ingestion job information is unavailable for this file.</p>
                </div>
                <p style={{ fontSize: 14, lineHeight: "17.5px", fontWeight: 500, color: "#201f1c" }}>
                  Ingestion tools unavailable
                </p>
                <p style={{ fontSize: 14, lineHeight: "20px", color: "#201f1c" }}>
                  The file is verified in Cloudflare R2 (<code>{object.bucket}</code>). RAG indexing jobs and retry endpoints are not exposed on <code>/api/admin/knowledge</code>.
                </p>
                <div>
                  <button
                    type="button"
                    className={`${styles.figmaBtn} ${styles.figmaBtnPrimary}`}
                    disabled
                  >
                    Retry ingestion
                  </button>
                </div>
              </div>

              <div className={styles.notice}>
                <DesignIcon name="details-Info" />
                <div className={styles.noticeBody}>
                  <p>
                    Replace file requires a versioned draft revision contract. The current R2 storage backend prevents overwriting existing keys.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      <DeleteFileDialog
        file={deleting && object ? object : null}
        close={() => setDeleting(false)}
        deleted={() => router.push(libraryHref(folderPrefix))}
      />
    </section>
  );
}
