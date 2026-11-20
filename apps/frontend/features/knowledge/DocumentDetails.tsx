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
import view from "./document-details.module.css";

function parentFolderPrefix(root: string, key: string): string {
  const slash = key.lastIndexOf("/");
  const candidate = slash < 0 ? root : key.slice(0, slash + 1);
  return candidate.startsWith(root) ? candidate : root;
}

function updatedAt(value: string): string {
  return new Date(value).toLocaleString("en-GB", { timeZone: "UTC", dateStyle: "medium", timeStyle: "short" });
}

export function DocumentDetails() {
  const query = useSearchParams(), router = useRouter(), { message } = App.useApp(), { root } = useKnowledge();
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
    setObject(null); setPreview(null); setDeleting(false);
    setObjectError(undefined); setPreviewError(undefined);
    if (!key) {
      setObjectLoading(false); setPreviewLoading(false);
      setObjectError(new ApiError("Select a document to view its details.", 422));
      return;
    }
    const controller = new AbortController();
    setObjectLoading(true); setPreviewLoading(true);
    void knowledgeApi.object(key, controller.signal).then(result => {
      if (!controller.signal.aborted) { setObject(result); setObjectLoading(false); }
    }).catch(error => {
      if (!isAborted(error) && !controller.signal.aborted) { setObjectError(error); setObjectLoading(false); }
    });
    void knowledgeApi.preview(key, controller.signal).then(result => {
      if (!controller.signal.aborted) { setPreview(result); setPreviewLoading(false); }
    }).catch(error => {
      if (!isAborted(error) && !controller.signal.aborted) { setPreviewError(error); setPreviewLoading(false); }
    });
    return () => controller.abort();
  }, [key, attempt]);

  // A changed URL must never briefly expose actions for the previous document.
  const currentObject = object?.key === key ? object : null;
  const currentPreview = preview?.key === key ? preview : null;
  const loading = objectLoading || Boolean(key && !currentObject && !objectError);
  const folderPrefix = parentFolderPrefix(root, key);
  const previewStatus = previewError instanceof ApiError ? previewError.status : undefined;

  async function handleDownload() {
    if (!currentObject) return;
    try { await downloadKnowledgeFile(currentObject.key); }
    catch (error) { void message.error(knowledgeError(error)); }
  }

  return (
    <section className={styles.page + " " + view.page} aria-label="Document details">
      <KnowledgeBreadcrumbs prefix={folderPrefix} current={currentObject?.name || "Document details"} />
      <header className={view.header}>
        <div className={view.titleBlock}>
          <h1>Document details</h1>
          <p>{currentObject ? currentObject.name + " · " + formatFileSize(currentObject.size) : "View the original document and its storage details."}</p>
        </div>
        <div className={styles.actions}>
          {currentObject ? <>
            <Button onClick={() => void handleDownload()}>View original</Button>
            <Button onClick={() => void handleDownload()}>Download file</Button>
            <Tooltip title="Versioned file replacement is not enabled.">
              <Button disabled>Replace file</Button>
            </Tooltip>
          </> : <Link href={libraryHref(folderPrefix)}><Button>Back to library</Button></Link>}
        </div>
      </header>

      {loading ? <KnowledgeFeedback loading /> : objectError || !currentObject ? (
        <KnowledgeFeedback error={objectError} retry={() => setAttempt(n => n + 1)} />
      ) : <>
        <div className={view.statusCards}>
          <section className={view.statusCard}>
            <div className={view.statusHeading}><span>Storage</span><span className={styles.badges}>Stored in R2</span></div>
            <p>Original file is stored and available to download.</p>
          </section>
          <section className={view.statusCard}>
            <div className={view.statusHeading}><span>Review</span><span className={styles.badges}>Unavailable</span></div>
            <p>Review tools are not enabled for this document.</p>
          </section>
          <section className={view.statusCard}>
            <div className={view.statusHeading}><span>Ingestion</span><span className={styles.badges}>Unavailable</span></div>
            <p>Ingestion is not enabled. Chatbot availability is unknown.</p>
          </section>
        </div>

        <div className={view.columns}>
          <div className={view.column}>
            <section className={view.panel}>
              <div className={view.panelHeading}>
                <div><h2>Text preview</h2><p className={view.description}>Original file content · UTF-8 text</p></div>
                <Button size="small" onClick={() => void handleDownload()}>Download original</Button>
              </div>
              {previewLoading ? <KnowledgeFeedback loading /> : currentPreview ? (
                <pre className={view.textPreview} aria-label="Raw text preview">{currentPreview.content}</pre>
              ) : (
                <div className={view.previewUnavailable} role="status">
                  <DesignIcon name="details-Info" />
                  <div><strong>{previewStatus === 413 ? "This file is too large to preview" : previewStatus === 404 ? "The original file was not found" : "Preview is not available"}</strong>
                    <p>{previewStatus === 413 || previewStatus === 415 || previewStatus === 422
                      ? "Download the original file to view its contents." : knowledgeError(previewError)}</p>
                    <Button size="small" onClick={() => void handleDownload()}>Download file</Button>
                  </div>
                </div>
              )}
            </section>

            <section className={view.panel}>
              <h2>Chunks</h2>
              <p className={view.description}>No extracted chunks are available for this document.</p>
              <div className={view.tableScroll}>
                <table className={view.chunkTable} aria-label="Document chunks">
                  <thead><tr><th>Chunk</th><th>Page</th><th>Content preview</th><th>Tokens</th></tr></thead>
                  <tbody><tr><td colSpan={4}>Chunk inspection is not enabled.</td></tr></tbody>
                </table>
              </div>
              <div className={view.panelFooter}><span>Ingestion data is unavailable.</span><Button size="small" disabled>View all chunks</Button></div>
            </section>
          </div>

          <div className={view.column}>
            <section className={view.panel}>
              <div className={view.panelHeading}><h2>Metadata and original file</h2><Link href={documentHref("metadata", currentObject.key)}>View metadata</Link></div>
              <dl className={view.metadata}>
                <div className={view.fullWidth}><dt>Title</dt><dd className={view.missing}>Editorial metadata is not available.</dd></div>
                <div className={view.fullWidth + " " + view.fileSection}><dt>Original filename</dt><dd>{currentObject.name}</dd></div>
                <div><dt>Format</dt><dd>{currentObject.name.includes(".") ? currentObject.name.split(".").pop()?.toUpperCase() : "FILE"}</dd></div>
                <div><dt>Size</dt><dd>{formatFileSize(currentObject.size)}</dd></div>
                <div className={view.fullWidth}><dt>R2 bucket</dt><dd>{currentObject.bucket}</dd></div>
                <div className={view.fullWidth}><dt>R2 object key</dt><dd><code>{currentObject.key}</code></dd></div>
                <div><dt>Uploaded by</dt><dd className={view.missing}>Not provided</dd></div>
                <div><dt>Updated (UTC)</dt><dd><time dateTime={currentObject.lastModified}>{updatedAt(currentObject.lastModified)}</time></dd></div>
              </dl>
              <details className={view.technicalDetails}><summary>Technical details</summary><dl className={view.metadata}>
                <div className={view.fullWidth}><dt>Content type</dt><dd>{currentObject.contentType}</dd></div>
                <div className={view.fullWidth}><dt>ETag</dt><dd><code>{currentObject.etag || "—"}</code></dd></div>
              </dl></details>
              <div className={view.fileActions}><Link href={libraryHref(folderPrefix)}>Back to folder</Link><Button danger type="text" size="small" onClick={() => setDeleting(true)}>Delete file</Button></div>
            </section>

            <section className={view.panel}>
              <h2>Ingestion</h2>
              <p className={view.description}>No processing job is available for this document.</p>
              <p className={view.bodyText}>Processing status, errors and retry tools are not enabled.</p>
              <Tooltip title="Ingestion tools are not enabled for this library."><Button disabled>Retry ingestion</Button></Tooltip>
            </section>
            <div className={view.notice}><DesignIcon name="details-Info" /><p>Storage, review and ingestion are independent. Uploading a file does not make it available to the chatbot.</p></div>
          </div>
        </div>
      </>}

      <DeleteFileDialog file={deleting && currentObject ? currentObject : null} close={() => setDeleting(false)} deleted={() => router.push(libraryHref(folderPrefix))} />
    </section>
  );
}
