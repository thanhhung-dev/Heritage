"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { App, Button, Input, Select, Tooltip } from "antd";
import { ApiError } from "../../lib/api";
import { isAborted, knowledgeApi, knowledgeError } from "../../services/knowledge.service";
import { DesignIcon } from "./DesignIcon";
import { KnowledgeBreadcrumbs } from "./FolderBrowser";
import { documentHref, libraryHref } from "./folder-state";
import { formatFileSize } from "./file-policy";
import { downloadKnowledgeFile } from "./knowledge-actions";
import { KnowledgeFeedback } from "./KnowledgeFeedback";
import { useKnowledge } from "./KnowledgeProvider";
import type { KnowledgeObject } from "./types";
import styles from "./knowledge.module.css";
import view from "./document-details.module.css";

function parentFolderPrefix(root: string, key: string): string {
  const slash = key.lastIndexOf("/");
  const candidate = slash < 0 ? root : key.slice(0, slash + 1);
  return candidate.startsWith(root) ? candidate : root;
}

const unavailableNotice = "Metadata editing and review tools are not enabled for this library.";

export function EditDocumentMetadata() {
  const query = useSearchParams(), { root } = useKnowledge(), { message } = App.useApp();
  const key = query.get("key") ?? "";
  const [object, setObject] = useState<KnowledgeObject | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>();
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    setObject(null); setError(undefined);
    if (!key) {
      setLoading(false);
      setError(new ApiError("Select a document to view its metadata.", 422));
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    void knowledgeApi.object(key, controller.signal).then(result => {
      if (!controller.signal.aborted) { setObject(result); setLoading(false); }
    }).catch(err => {
      if (!isAborted(err) && !controller.signal.aborted) { setError(err); setLoading(false); }
    });
    return () => controller.abort();
  }, [key, attempt]);

  const currentObject = object?.key === key ? object : null;
  const waiting = loading || Boolean(key && !currentObject && !error);
  const folderPrefix = parentFolderPrefix(root, key);
  async function viewOriginal() {
    if (!currentObject) return;
    try { await downloadKnowledgeFile(currentObject.key); }
    catch (err) { void message.error(knowledgeError(err)); }
  }

  return (
    <section className={styles.page + " " + view.page} aria-label="Edit document metadata">
      <KnowledgeBreadcrumbs prefix={folderPrefix} current={currentObject ? currentObject.name + " / Edit metadata" : "Edit metadata"} />
      <header className={view.header}>
        <div className={view.titleBlock}><h1>Edit document metadata</h1><p>{currentObject ? currentObject.name + " · Stored in R2" : "Document metadata and original file properties."}</p></div>
        {currentObject ? <Button onClick={() => void viewOriginal()}>View original</Button> : <Link href={libraryHref(folderPrefix)}><Button>Back to library</Button></Link>}
      </header>

      {waiting ? <KnowledgeFeedback loading /> : error || !currentObject ? (
        <KnowledgeFeedback error={error} retry={() => setAttempt(n => n + 1)} />
      ) : <>
        <div className={view.statusCards}>
          <section className={view.statusCard}><div className={view.statusHeading}><span>Storage</span><span className={styles.badges}>Stored in R2</span></div><p>Original file retained in Cloudflare R2.</p></section>
          <section className={view.statusCard}><div className={view.statusHeading}><span>Review</span><span className={styles.badges}>Unavailable</span></div><p>Review tools are not enabled for this document.</p></section>
          <section className={view.statusCard}><div className={view.statusHeading}><span>Ingestion</span><span className={styles.badges}>Unavailable</span></div><p>Ingestion is not enabled. Chatbot availability is unknown.</p></section>
        </div>

        <div className={view.columns}>
          <div className={view.column}>
            <section className={view.panel}>
              <h2>Document metadata</h2>
              <p className={view.description}>Metadata editing is not enabled yet. The original file is available to view and download.</p>
              <form className={view.metadataForm} aria-label="Document metadata unavailable" onSubmit={event => event.preventDefault()}>
                <div className={view.field}>
                  <label htmlFor="doc-meta-title">Document title <span aria-hidden="true">*</span></label>
                  <Input id="doc-meta-title" disabled value="" placeholder="Not available" />
                  <p className={view.fieldHint}>The document title is separate from the original filename.</p>
                </div>
                <div className={view.fieldPair}>
                  <div className={view.field}><label htmlFor="doc-meta-region">Region <span aria-hidden="true">*</span></label>
                    <Select id="doc-meta-region" disabled value="unavailable" suffixIcon={<DesignIcon name="edit-metadata-ChevronDown" />} options={[{ value: "unavailable", label: "Not available" }]} />
                  </div>
                  <div className={view.field}><label htmlFor="doc-meta-type">Document type <span aria-hidden="true">*</span></label>
                    <Select id="doc-meta-type" disabled value="unavailable" suffixIcon={<DesignIcon name="edit-metadata-ChevronDown" />} options={[{ value: "unavailable", label: "Not available" }]} />
                  </div>
                </div>
                <div className={view.field}><label htmlFor="doc-meta-citation">Citation source URL <span aria-hidden="true">*</span></label>
                  <Input id="doc-meta-citation" disabled value="" placeholder="Not available" />
                  <p className={view.fieldHint}>Use the source document URL, not a temporary R2 download link.</p>
                </div>
                <div className={view.inlineNotice}><DesignIcon name="edit-metadata-Info" /><div><strong>Editing is not available yet</strong><p>Draft saving and submission will be available when review tools are enabled.</p></div></div>
                <div className={view.formFooter}>
                  <Link href={documentHref("details", currentObject.key)}><Button>Cancel</Button></Link>
                  <div className={styles.actions}><Tooltip title={unavailableNotice}><Button disabled>Save draft</Button></Tooltip><Tooltip title={unavailableNotice}><Button type="primary" disabled>Submit for review</Button></Tooltip></div>
                </div>
              </form>
            </section>

            <section className={view.panel}>
              <h2>Before submitting</h2>
              <p className={view.description}>Review submission is not available for this document.</p>
              <div className={view.checklist}>
                <div><DesignIcon name="edit-metadata-Info" /><span><strong>Identify the document</strong><small>Title, region and type describe the document.</small></span></div>
                <div><DesignIcon name="edit-metadata-Info" /><span><strong>Verify the source</strong><small>A citation should point to the original source.</small></span></div>
              </div>
              <p className={view.fieldHint}>Saving metadata and storing the original file are separate actions.</p>
            </section>
          </div>

          <div className={view.column}>
            <section className={view.panel}>
              <h2>Original file</h2>
              <p className={view.description}>Read-only file properties.</p>
              <dl className={view.metadata}>
                <div className={view.fullWidth}><dt>Original filename</dt><dd>{currentObject.name}</dd></div>
                <div><dt>Format</dt><dd>{currentObject.name.includes(".") ? currentObject.name.split(".").pop()?.toUpperCase() : "FILE"}</dd></div>
                <div><dt>Size</dt><dd>{formatFileSize(currentObject.size)}</dd></div>
                <div className={view.fullWidth}><dt>Cloudflare R2 bucket</dt><dd>{currentObject.bucket}</dd></div>
                <div className={view.fullWidth}><dt>R2 object key</dt><dd><code>{currentObject.key}</code></dd></div>
                <div><dt>Uploaded by</dt><dd className={view.missing}>Not provided</dd></div>
                <div><dt>Last updated (UTC)</dt><dd><time dateTime={currentObject.lastModified}>{new Date(currentObject.lastModified).toLocaleString("en-GB", { timeZone: "UTC", dateStyle: "medium", timeStyle: "short" })}</time></dd></div>
              </dl>
              <details className={view.technicalDetails}><summary>Technical details</summary><dl className={view.metadata}>
                <div className={view.fullWidth}><dt>Content type</dt><dd>{currentObject.contentType}</dd></div>
                <div className={view.fullWidth}><dt>ETag</dt><dd><code>{currentObject.etag || "—"}</code></dd></div>
              </dl></details>
            </section>
            <section className={view.panel}><h2>Editing permissions</h2><p className={view.bodyText}>You are viewing this document with administrator access. Metadata editing and review tools are not enabled yet.</p></section>
            <div className={view.notice}><DesignIcon name="edit-metadata-Info" /><p>Review is separate from ingestion. Storing a file does not approve it or make it available to the chatbot.</p></div>
          </div>
        </div>
      </>}
    </section>
  );
}
