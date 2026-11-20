"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { App, Tooltip } from "antd";
import { ApiError } from "../../lib/api";
import { isAborted, knowledgeApi, knowledgeError } from "../../services/knowledge.service";
import { DesignIcon } from "./DesignIcon";
import { KnowledgeTopPath } from "./FolderBrowser";
import { documentHref, libraryHref } from "./folder-state";
import { formatFileSize } from "./file-policy";
import { downloadKnowledgeFile } from "./knowledge-actions";
import { KnowledgeFeedback } from "./KnowledgeFeedback";
import { useKnowledge } from "./KnowledgeProvider";
import { useAdminSession } from "./useAdminSession";
import type { KnowledgeObject } from "./types";
import styles from "./knowledge.module.css";

function parentFolderPrefix(root: string, key: string): string {
  const slashIndex = key.lastIndexOf("/");
  if (slashIndex === -1) return root;
  const candidate = key.slice(0, slashIndex + 1);
  return candidate.startsWith(root) ? candidate : root;
}

const unavailableNotice = "Editorial metadata persistence and review submission endpoints are not exposed by the mounted backend contract.";

export function EditDocumentMetadata() {
  const query = useSearchParams();
  const { message } = App.useApp();
  const { root } = useKnowledge();
  const { user } = useAdminSession();
  const key = query.get("key") ?? "";

  const [object, setObject] = useState<KnowledgeObject | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>();
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!key) {
      setObject(null);
      setLoading(false);
      setError(new ApiError("Select a document key to inspect metadata.", 422));
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(undefined);
    void knowledgeApi.object(key, controller.signal)
      .then(result => {
        if (!controller.signal.aborted) {
          setObject(result);
          setLoading(false);
        }
      })
      .catch(err => {
        if (!isAborted(err) && !controller.signal.aborted) {
          setObject(null);
          setError(err);
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [key, attempt]);

  const folderPrefix = parentFolderPrefix(root, key);
  const ext = object?.name.includes(".") ? object.name.split(".").pop()?.toUpperCase() : "FILE";
  const viewerName = user?.display_name || user?.username || "Administrator";

  async function handleViewOriginal() {
    if (!key) return;
    try {
      await downloadKnowledgeFile(key);
    } catch (e) {
      void message.error(knowledgeError(e));
    }
  }

  return (
    <section className={styles.page} aria-label="Edit document metadata">
      <KnowledgeTopPath
        prefix={folderPrefix}
        fileLabel={object?.name || key || "Document"}
        current="Edit metadata"
      />

      <header className={styles.header}>
        <div>
          <h1>Edit document metadata</h1>
          <p>
            {object
              ? `${object.name} · Stored in R2 · Review workflow unavailable`
              : "Inspect storage metadata and editorial fields"}
          </p>
        </div>
        <div className={styles.actions}>
          {object && (
            <>
              <Link href={documentHref("details", object.key)} className={styles.figmaBtn}>
                Document details
              </Link>
              <button type="button" className={styles.figmaBtn} onClick={() => void handleViewOriginal()}>
                View original
              </button>
            </>
          )}
        </div>
      </header>

      <div className={styles.contextBar}>
        <span className={styles.contextBadge}>CLOUDFLARE R2</span>
        <span className={styles.contextText}>
          Original file properties are read from <code>GET /api/admin/knowledge/object</code> · Editorial draft persistence is not available in the current backend
        </span>
      </div>

      {loading ? (
        <KnowledgeFeedback loading />
      ) : error || !object ? (
        <KnowledgeFeedback error={error} retry={() => setAttempt(n => n + 1)} />
      ) : (
        <>
          <div className={styles.stateCards}>
            <div className={styles.stateCard}>
              <div className={styles.stateTitle}>
                <span className={styles.stateLabel}>Storage</span>
                <span className={styles.badges}>Stored in R2</span>
              </div>
              <p className={styles.stateSummary}>Original file retained in Cloudflare R2.</p>
            </div>
            <div className={styles.stateCard}>
              <div className={styles.stateTitle}>
                <span className={styles.stateLabel}>Review</span>
                <span className={styles.badges}>Unavailable</span>
              </div>
              <p className={styles.stateSummary}>Review status is not reported for this file.</p>
            </div>
            <div className={styles.stateCard}>
              <div className={styles.stateTitle}>
                <span className={styles.stateLabel}>Ingestion</span>
                <span className={styles.badges}>Unavailable</span>
              </div>
              <p className={styles.stateSummary}>Ingestion and chatbot availability are not reported.</p>
            </div>
          </div>

          <div className={styles.twoColumnsMetadata}>
            <div className={styles.mainColumn} style={{ gap: 20 }}>
              <div className={styles.panel}>
                <div className={styles.panelHeading}>
                  <h2>Document metadata</h2>
                  <p>Fields marked * are required to submit a revision for review once editorial persistence is enabled.</p>
                </div>

                <div className={styles.fieldGroup}>
                  <div className={styles.fieldRow}>
                    <label htmlFor="doc-meta-title">Document title *</label>
                    <div className={styles.readonlyControl} id="doc-meta-title">
                      <span>{object.name.replace(/\.[^.]+$/, "")}</span>
                    </div>
                    <span className={styles.muted}>
                      Use a descriptive title. The original filename is kept separately.
                    </span>
                  </div>

                  <div className={styles.metaTwoCols}>
                    <div className={styles.fieldRow}>
                      <label htmlFor="doc-meta-region">Region *</label>
                      <div className={styles.readonlyControl} id="doc-meta-region">
                        <span>{object.metadata?.["region"] || "Not provided"}</span>
                        <DesignIcon name="edit-metadata-ChevronDown" />
                      </div>
                    </div>

                    <div className={styles.fieldRow}>
                      <label htmlFor="doc-meta-type">Document type *</label>
                      <div className={styles.readonlyControl} id="doc-meta-type">
                        <span>{object.metadata?.["document-type"] || "Not provided"}</span>
                        <DesignIcon name="edit-metadata-ChevronDown" />
                      </div>
                    </div>
                  </div>

                  <div className={styles.fieldRow}>
                    <label htmlFor="doc-meta-citation">Citation source URL *</label>
                    <div className={styles.readonlyControl} id="doc-meta-citation">
                      <span className={styles.muted}>Not persisted by current R2 backend</span>
                    </div>
                    <span className={styles.muted}>
                      Use the source document URL, not a temporary R2 download link.
                    </span>
                  </div>
                </div>

                <div className={styles.notice}>
                  <DesignIcon name="edit-metadata-Info" />
                  <div className={styles.noticeBody}>
                    <span className={styles.noticeTitle}>Save without submitting</span>
                    <p>
                      Metadata editing is not available yet. The original file remains stored in R2.
                    </p>
                  </div>
                </div>

                <div className={styles.dividerTop} style={{ flexDirection: "row", alignItems: "center", paddingTop: 16 }}>
                  <Link href={libraryHref(folderPrefix)} className={styles.figmaBtn}>
                    Cancel
                  </Link>
                  <div style={{ flex: 1 }} />
                  <Tooltip title={unavailableNotice}>
                    <button type="button" className={styles.figmaBtn} disabled>
                      Save draft
                    </button>
                  </Tooltip>
                  <Tooltip title={unavailableNotice}>
                    <button type="button" className={`${styles.figmaBtn} ${styles.figmaBtnPrimary}`} disabled>
                      Submit for review
                    </button>
                  </Tooltip>
                </div>
              </div>

              <div className={styles.panel}>
                <div className={styles.panelHeading}>
                  <h2>Before submitting</h2>
                  <p>Required metadata checks before submitting a document revision for review.</p>
                </div>

                <div className={styles.checklistGrid}>
                  <div className={styles.checklistItem}>
                    <DesignIcon name="edit-metadata-CircleCheck" />
                    <div className={styles.checklistText}>
                      <span className={styles.checklistTitle}>Identify the document</span>
                      <span className={styles.checklistDesc}>Title, region, and type describe this revision.</span>
                    </div>
                  </div>
                  <div className={styles.checklistItem}>
                    <DesignIcon name="edit-metadata-CircleCheck" />
                    <div className={styles.checklistText}>
                      <span className={styles.checklistTitle}>Verify the source</span>
                      <span className={styles.checklistDesc}>Citation URL points to a permanent source address.</span>
                    </div>
                  </div>
                </div>

                <p className={styles.muted}>
                  Saving drafts and submitting for review will be available when review tools are enabled.
                </p>
              </div>
            </div>

            <div className={styles.mainColumn} style={{ gap: 20 }}>
              <div className={styles.panel}>
                <div className={styles.panelHeading}>
                  <h2>Original file</h2>
                  <p>Read-only file properties · This form inspects metadata only.</p>
                </div>

                <div className={styles.metaStack}>
                  <div className={styles.metaField}>
                    <span className={styles.metaFieldLabel}>Original filename</span>
                    <span className={styles.metaFieldValue}>{object.name}</span>
                  </div>

                  <div className={styles.metaTwoCols}>
                    <div className={styles.metaField}>
                      <span className={styles.metaFieldLabel}>Format</span>
                      <span className={styles.metaFieldValue}>{ext} ({object.contentType})</span>
                    </div>
                    <div className={styles.metaField}>
                      <span className={styles.metaFieldLabel}>Size</span>
                      <span className={styles.metaFieldValue}>{formatFileSize(object.size)}</span>
                    </div>
                  </div>

                  <div className={styles.metaField}>
                    <span className={styles.metaFieldLabel}>Cloudflare R2 bucket</span>
                    <span className={styles.metaFieldValue}>{object.bucket}</span>
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
                      <span className={styles.metaFieldLabel}>Last updated (UTC)</span>
                      <span className={styles.metaFieldValue}>
                        {new Date(object.lastModified).toLocaleString("en-GB", {
                          timeZone: "UTC",
                          dateStyle: "medium",
                          timeStyle: "short",
                        })}
                      </span>
                    </div>
                  </div>
                </div>

                <p className={styles.muted}>
                  Changing the region classifies the document; it does not move the stored R2 object.
                </p>
              </div>

              <div className={styles.panel}>
                <div className={styles.panelHeading}>
                  <h2>Editing permissions</h2>
                </div>
                <p style={{ fontSize: 14, lineHeight: "20px", color: "#201f1c" }}>
                  {viewerName} is viewing this object with verified Administrator access.
                </p>
                <p className={styles.muted}>
                  Ownership and review-state checks must be enforced by the backend. This form is read-only until editorial metadata persistence is added.
                </p>
              </div>

              <div className={styles.notice}>
                <DesignIcon name="edit-metadata-Info" />
                <div className={styles.noticeBody}>
                  <span className={styles.noticeTitle}>Review is separate from indexing</span>
                  <p>
                    Submission requests an Admin decision. Approval alone does not publish the document. Chatbot availability requires successful ingestion and an Indexed state in OpenSearch.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
