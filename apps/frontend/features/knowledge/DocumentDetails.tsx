"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { App, Button, Tooltip } from "antd";
import { ApiError } from "../../lib/api";
import { isAborted, knowledgeApi, knowledgeError } from "../../services/knowledge.service";
import { DesignIcon } from "./DesignIcon";
import { DeleteFileDialog } from "./FileDialogs";
import { KnowledgeBreadcrumbs } from "./FolderBrowser";
import { documentHref, libraryHref } from "./folder-state";
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

  const [attempt, setAttempt] = useState(0);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
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
  const previewStatus = previewError instanceof ApiError ? previewError.status : undefined;

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
      <KnowledgeBreadcrumbs prefix={folderPrefix} current={object?.name || key || "Document details"} />

      <header className={styles.header}>
        <div>
          <h1>{object?.name || key || "Document details"}</h1>
          <p>Inspect Cloudflare R2 object properties, safe plain-text preview, and independent review and ingestion states.</p>
        </div>
        <div className={styles.actions}>
          <Link href={libraryHref(folderPrefix)}>
            <Button icon={<DesignIcon name="library-ArrowLeft" />}>Back to folder</Button>
          </Link>
          {object && (
            <>
              <Link href={documentHref("metadata", object.key)}>
                <Button>Edit metadata</Button>
              </Link>
              <Button onClick={() => void handleDownload()}>View original / Download</Button>
              <Tooltip title="Versioned replacement is not supported by the current R2 backend contract.">
                <Button disabled>Replace file</Button>
              </Tooltip>
              <Button danger onClick={() => setDeleting(true)}>Delete file</Button>
            </>
          )}
        </div>
      </header>

      {objectLoading ? (
        <KnowledgeFeedback loading />
      ) : objectError || !object ? (
        <KnowledgeFeedback error={objectError} retry={() => setAttempt(n => n + 1)} />
      ) : (
        <>
          <div className={styles.stateCards}>
            <div className={styles.panel}>
              <div className={styles.stateTitle}>
                <strong>Storage status</strong>
                <span className={styles.badges}>Stored in R2</span>
              </div>
              <p className={styles.muted}>
                Object is physically stored in bucket <code>{object.bucket}</code> under exact key <code>{object.key}</code>.
              </p>
            </div>
            <div className={styles.panel}>
              <div className={styles.stateTitle}>
                <strong>Review status</strong>
                <span className={styles.badges}>Unavailable</span>
              </div>
              <p className={styles.muted}>
                The backend does not provide a review state for this R2 object. Storage completion does not imply editorial approval.
              </p>
            </div>
            <div className={styles.panel}>
              <div className={styles.stateTitle}>
                <strong>Ingestion status</strong>
                <span className={styles.badges}>Unavailable</span>
              </div>
              <p className={styles.muted}>
                No RAG ingestion job endpoint is attached to this library object. The file is not automatically indexed or exposed to the chatbot.
              </p>
            </div>
          </div>

          <div className={styles.twoColumns}>
            <div className={styles.mainColumn}>
              <div className={styles.panel}>
                <div className={styles.replacementHeader}>
                  <div>
                    <h2>Raw UTF-8 text preview</h2>
                    <p className={styles.muted}>
                      Rendered safely as plain text from R2 without executing HTML or Markdown.
                    </p>
                  </div>
                  <Button size="small" onClick={() => void handleDownload()}>Download original</Button>
                </div>

                {previewLoading ? (
                  <KnowledgeFeedback loading />
                ) : preview ? (
                  <pre className={styles.previewBox} aria-label="Raw text preview">{preview.content}</pre>
                ) : (
                  <div className={styles.error} role="alert">
                    <strong>
                      {previewStatus === 413
                        ? "File exceeds the preview size limit (413)"
                        : previewStatus === 404
                        ? "Object not found for preview (404)"
                        : previewStatus === 422 || previewStatus === 415
                        ? "Preview not supported for this content"
                        : "Preview unavailable"}
                    </strong>
                    <p>{knowledgeError(previewError)}</p>
                    <Button size="small" onClick={() => void handleDownload()}>Download file instead</Button>
                  </div>
                )}
              </div>

              <div className={styles.panel}>
                <h2>Extracted text & RAG chunks</h2>
                <p className={styles.muted}>
                  Chunk inspection and extracted-text pipelines are not exposed by the mounted <code>/api/admin/knowledge</code> contract. No chunks or embeddings are fabricated in the UI.
                </p>
              </div>
            </div>

            <div className={styles.mainColumn}>
              <div className={styles.panel}>
                <h2>File information (R2 HEAD)</h2>
                <dl className={styles.metaGrid}>
                  <div className={styles.metaItem}>
                    <dt>Filename</dt>
                    <dd>{object.name}</dd>
                  </div>
                  <div className={styles.metaItem}>
                    <dt>Bucket</dt>
                    <dd>{object.bucket}</dd>
                  </div>
                  <div className={styles.metaItem}>
                    <dt>Exact object key</dt>
                    <dd><code>{object.key}</code></dd>
                  </div>
                  <div className={styles.metaItem}>
                    <dt>Content type</dt>
                    <dd>{object.contentType}</dd>
                  </div>
                  <div className={styles.metaItem}>
                    <dt>Size</dt>
                    <dd>{formatFileSize(object.size)} ({object.size} bytes)</dd>
                  </div>
                  <div className={styles.metaItem}>
                    <dt>Last modified (UTC)</dt>
                    <dd>{new Date(object.lastModified).toUTCString()}</dd>
                  </div>
                  <div className={styles.metaItem}>
                    <dt>ETag</dt>
                    <dd><code>{object.etag || "—"}</code></dd>
                  </div>
                  <div className={styles.metaItem}>
                    <dt>Uploaded by</dt>
                    <dd>Not provided by backend</dd>
                  </div>
                </dl>
              </div>

              <div className={styles.panel}>
                <h2>Processing errors & retry ingestion</h2>
                <p className={styles.muted}>
                  Because RAG ingestion jobs are not wired for <code>knowledge-heritage</code> objects in the current backend, no processing errors or retry actions are available.
                </p>
                <div className={styles.actions} style={{ marginTop: 12 }}>
                  <Button disabled>Retry ingestion (unavailable)</Button>
                </div>
              </div>

              <div className={styles.panel}>
                <h2>Replace original file</h2>
                <p className={styles.muted}>
                  The upload contract enforces immutable object keys and rejects filename conflicts (HTTP 409). Safe versioned replacement is not yet supported by the backend.
                </p>
                <div className={styles.actions} style={{ marginTop: 12 }}>
                  <Button disabled>Replace file (unavailable)</Button>
                </div>
              </div>
            </div>
          </div>

          <div className={styles.notice}>
            <DesignIcon name="details-Info" />
            <p>
              All properties above come directly from <code>GET /api/admin/knowledge/object</code> and <code>GET /api/admin/knowledge/preview</code>.
            </p>
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
