"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Button, Input, Select, Tooltip } from "antd";
import { ApiError } from "../../lib/api";
import { isAborted, knowledgeApi } from "../../services/knowledge.service";
import { DesignIcon } from "./DesignIcon";
import { KnowledgeBreadcrumbs } from "./FolderBrowser";
import { documentHref, libraryHref } from "./folder-state";
import { formatFileSize } from "./file-policy";
import { KnowledgeFeedback } from "./KnowledgeFeedback";
import { useKnowledge } from "./KnowledgeProvider";
import type { KnowledgeObject } from "./types";
import styles from "./knowledge.module.css";

function parentFolderPrefix(root: string, key: string): string {
  const slashIndex = key.lastIndexOf("/");
  if (slashIndex === -1) return root;
  const candidate = key.slice(0, slashIndex + 1);
  return candidate.startsWith(root) ? candidate : root;
}

const unavailableNotice = "Editorial metadata persistence and review transitions are not available in the mounted backend contract.";

export function EditDocumentMetadata() {
  const query = useSearchParams();
  const { root } = useKnowledge();
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

  return (
    <section className={styles.page} aria-label="Edit document metadata">
      <KnowledgeBreadcrumbs prefix={folderPrefix} current={object ? `${object.name} · Metadata` : "Document metadata"} />

      <header className={styles.header}>
        <div>
          <h1>Edit document metadata</h1>
          <p>Inspect real Cloudflare R2 storage properties alongside editorial metadata fields defined in Figma.</p>
        </div>
        <div className={styles.actions}>
          <Link href={libraryHref(folderPrefix)}>
            <Button icon={<DesignIcon name="library-ArrowLeft" />}>Back to folder</Button>
          </Link>
          {object && (
            <Link href={documentHref("details", object.key)}>
              <Button>View document details</Button>
            </Link>
          )}
          <Tooltip title={unavailableNotice}>
            <Button disabled>Save draft</Button>
          </Tooltip>
          <Tooltip title={unavailableNotice}>
            <Button type="primary" disabled>Submit for review</Button>
          </Tooltip>
        </div>
      </header>

      {loading ? (
        <KnowledgeFeedback loading />
      ) : error || !object ? (
        <KnowledgeFeedback error={error} retry={() => setAttempt(n => n + 1)} />
      ) : (
        <>
          <div className={styles.stateCards}>
            <div className={styles.panel}>
              <div className={styles.stateTitle}>
                <strong>Storage status</strong>
                <span className={styles.badges}>Stored in R2</span>
              </div>
              <p className={styles.muted}>
                Verified in <code>{object.bucket}</code> at key <code>{object.key}</code>.
              </p>
            </div>
            <div className={styles.panel}>
              <div className={styles.stateTitle}>
                <strong>Review status</strong>
                <span className={styles.badges}>Unavailable</span>
              </div>
              <p className={styles.muted}>
                No persistent review status or revision workflow is exposed by the current backend.
              </p>
            </div>
            <div className={styles.panel}>
              <div className={styles.stateTitle}>
                <strong>Ingestion status</strong>
                <span className={styles.badges}>Unavailable</span>
              </div>
              <p className={styles.muted}>
                Not automatically indexed. No ingestion job API is connected to this R2 object.
              </p>
            </div>
          </div>

          <div className={styles.twoColumns}>
            <div className={styles.panel}>
              <h2>Editorial metadata (read-only until backend API is added)</h2>
              <p className={styles.muted}>
                The mounted <code>/api/admin/knowledge</code> endpoints store and inspect raw R2 objects. Because there is no database persistence endpoint for document title, region, document type, or citation URL on R2 library objects, these fields are disabled so drafts are never faked.
              </p>

              <div className={styles.fieldGroup}>
                <div className={styles.fieldRow}>
                  <label htmlFor="doc-meta-title">Document title</label>
                  <Input
                    id="doc-meta-title"
                    disabled
                    value={object.metadata?.title ?? ""}
                    placeholder="Not persisted by backend"
                  />
                </div>
                <div className={styles.fieldRow}>
                  <label htmlFor="doc-meta-region">Region</label>
                  <Select
                    id="doc-meta-region"
                    disabled
                    value="unavailable"
                    style={{ width: "100%" }}
                    options={[{ value: "unavailable", label: "Region metadata persistence unavailable" }]}
                  />
                </div>
                <div className={styles.fieldRow}>
                  <label htmlFor="doc-meta-type">Document type</label>
                  <Select
                    id="doc-meta-type"
                    disabled
                    value="unavailable"
                    style={{ width: "100%" }}
                    options={[{ value: "unavailable", label: "Document type persistence unavailable" }]}
                  />
                </div>
                <div className={styles.fieldRow}>
                  <label htmlFor="doc-meta-citation">Citation source URL</label>
                  <Input
                    id="doc-meta-citation"
                    disabled
                    value={object.metadata?.citationUrl ?? ""}
                    placeholder="https://... (editorial persistence unavailable)"
                  />
                </div>
              </div>

              <div className={styles.actions} style={{ marginTop: 20 }}>
                <Tooltip title={unavailableNotice}>
                  <Button disabled>Save draft (unavailable)</Button>
                </Tooltip>
                <Tooltip title={unavailableNotice}>
                  <Button type="primary" disabled>Submit for review (unavailable)</Button>
                </Tooltip>
              </div>
            </div>

            <div className={styles.mainColumn}>
              <div className={styles.panel}>
                <h2>Original file properties (R2 HEAD)</h2>
                <dl className={styles.metaGrid}>
                  <div className={styles.metaItem}>
                    <dt>Original filename</dt>
                    <dd>{object.name}</dd>
                  </div>
                  <div className={styles.metaItem}>
                    <dt>Format & size</dt>
                    <dd>{object.contentType} · {formatFileSize(object.size)}</dd>
                  </div>
                  <div className={styles.metaItem}>
                    <dt>Exact object key</dt>
                    <dd><code>{object.key}</code></dd>
                  </div>
                  <div className={styles.metaItem}>
                    <dt>Last modified</dt>
                    <dd>{new Date(object.lastModified).toUTCString()}</dd>
                  </div>
                  <div className={styles.metaItem}>
                    <dt>ETag</dt>
                    <dd><code>{object.etag || "—"}</code></dd>
                  </div>
                </dl>
              </div>

              <div className={styles.panel}>
                <h2>Permission & revision requirements</h2>
                <p className={styles.muted}>
                  All Knowledge R2 endpoints require an authenticated Administrator session. Editorial draft saving, revision locking, and review submission require dedicated backend persistence endpoints before they can be enabled.
                </p>
              </div>
            </div>
          </div>

          <div className={styles.notice}>
            <DesignIcon name="edit-metadata-Info" />
            <p>
              Storage state is verified directly from Cloudflare R2. Editorial metadata, review approval, and RAG ingestion are never simulated on the client.
            </p>
          </div>
        </>
      )}
    </section>
  );
}
