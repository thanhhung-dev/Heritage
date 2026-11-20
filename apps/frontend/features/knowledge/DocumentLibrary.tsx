"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { App, Dropdown, Tooltip } from "antd";
import { knowledgeError } from "../../services/knowledge.service";
import { DesignIcon } from "./DesignIcon";
import { FolderBrowser, KnowledgeBreadcrumbs } from "./FolderBrowser";
import { CreateFolderDialog, DeleteFileDialog } from "./FileDialogs";
import { UploadDocumentsModal } from "./UploadModal";
import { breadcrumbParts, documentHref, libraryHref, uploadHref } from "./folder-state";
import { formatFileSize } from "./file-policy";
import { KnowledgeFeedback } from "./KnowledgeFeedback";
import { useKnowledge } from "./KnowledgeProvider";
import { downloadKnowledgeFile } from "./knowledge-actions";
import { useKnowledgeFolder } from "./useKnowledgeFolder";
import type { KnowledgeFile } from "./types";
import styles from "./knowledge.module.css";

const pageSize = 10;
const advancedUnavailable = "The mounted R2 storage backend does not expose review or ingestion states for these files.";

function formatFigmaDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-GB", {
    timeZone: "UTC",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function fileFolderLabel(root: string, key: string): string {
  const slash = key.lastIndexOf("/");
  if (slash === -1) return "All documents";
  const folderPrefix = key.slice(0, slash + 1);
  const parts = breadcrumbParts(root, folderPrefix);
  return parts.length ? parts.map(p => p.label).join(" / ") : "All documents";
}

export function DocumentLibrary() {
  const query = useSearchParams();
  const router = useRouter();
  const { message } = App.useApp();
  const { root } = useKnowledge();
  const listing = useKnowledgeFolder(query.has("prefix") ? query.get("prefix")! : undefined);

  const [search, setSearch] = useState("");
  const searchInput = useRef<HTMLInputElement>(null);
  useEffect(() => { if (query.get("focus") === "search") searchInput.current?.focus(); }, [query]);
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [deleting, setDeleting] = useState<KnowledgeFile | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);

  useEffect(() => {
    setPage(1);
    setSearch("");
    setSelectedKey(null);
  }, [listing.prefix]);

  const files = listing.page?.files;
  const filtered = useMemo(
    () => (files ?? []).filter(file => file.name.toLocaleLowerCase().includes(search.toLocaleLowerCase())),
    [files, search],
  );

  useEffect(() => {
    if (!selectedKey && filtered.length > 0) {
      setSelectedKey(filtered[0].key);
    }
  }, [filtered, selectedKey]);

  const selected = files?.find(file => file.key === selectedKey) ?? null;
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const shownPage = Math.min(page, totalPages);
  const visible = filtered.slice((shownPage - 1) * pageSize, shownPage * pageSize);

  async function download(file: KnowledgeFile) {
    try {
      await downloadKnowledgeFile(file.key);
    } catch (e) {
      void message.error(knowledgeError(e));
    }
  }

  return (
    <section className={styles.page} aria-label="Document library">
      <header className={styles.header}>
        <div>
          <h1>Document library</h1>
          <p>Manage original files, metadata, review status, and ingestion in one place.</p>
        </div>
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.figmaBtn}
            disabled={listing.loading || Boolean(listing.error)}
            onClick={() => setCreateOpen(true)}
          >
            Create folder
          </button>
          <button
            type="button"
            className={`${styles.figmaBtn} ${styles.figmaBtnPrimary}`}
            disabled={listing.loading || Boolean(listing.error)}
            onClick={() => setUploadOpen(true)}
          >
            Upload documents
          </button>
        </div>
      </header>

      <div className={styles.contextBar}>
        <span className={styles.contextBadge}>CLOUDFLARE R2</span>
        <span className={styles.contextText}>
          Connected to bucket <code>knowledge-heritage</code> · Prefix: <code>{listing.prefix || "/"}</code> · Storage completion is separate from review and RAG indexing
        </span>
        <Link href={uploadHref(listing.prefix)} className={styles.rowActionLink}>
          Open full upload page
        </Link>
      </div>

      <div className={styles.workspace}>
        <FolderBrowser prefix={listing.prefix} onSelect={prefix => router.push(libraryHref(prefix))} />

        <div className={styles.mainColumn}>
          <KnowledgeBreadcrumbs prefix={listing.prefix} />

          <div className={styles.toolbar}>
            <input
              type="search"
              ref={searchInput}
              className={styles.searchInput}
              value={search}
              onChange={e => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search file names…"
              aria-label="Search loaded file names"
            />
            <Tooltip title={advancedUnavailable}>
              <div className={styles.filterPill} aria-label="Review filter unavailable">
                <span>Review: All</span>
                <DesignIcon name="library-ChevronDown" />
              </div>
            </Tooltip>
            <Tooltip title={advancedUnavailable}>
              <div className={styles.filterPill} aria-label="Ingestion filter unavailable">
                <span>Ingestion: All</span>
                <DesignIcon name="library-ChevronDown" />
              </div>
            </Tooltip>
            <div className={styles.toolbarSpacer} />
            <span className={styles.resultsNote}>
              {files?.length ?? 0} documents loaded · Review & ingestion unavailable
            </span>
          </div>

          {listing.loading ? (
            <KnowledgeFeedback loading />
          ) : listing.error ? (
            <KnowledgeFeedback error={listing.error} retry={listing.refresh} />
          ) : (
            <>
              <div className={styles.figmaTable} role="table" aria-label="Documents">
                <div className={styles.figmaTableHeader} role="row">
                  <div className={styles.colCheck} role="columnheader" aria-label="Select document" />
                  <div className={styles.colFile} role="columnheader">File name</div>
                  <div className={styles.colFormat} role="columnheader">Format / size</div>
                  <div className={styles.colUpdated} role="columnheader">Updated / uploaded by</div>
                  <div className={styles.colReview} role="columnheader">Review</div>
                  <div className={styles.colIngestion} role="columnheader">Ingestion</div>
                  <div className={styles.colActions} role="columnheader">Actions</div>
                </div>

                {visible.length === 0 ? (
                  <div className={styles.empty}>
                    <DesignIcon name="library-FolderOpen" />
                    <h2>{search ? "No matching files" : "No files in this folder"}</h2>
                    <p className={styles.muted}>
                      {search
                        ? "No loaded file names match your filter. Clear search or load more pages if available."
                        : "Open a folder from the sidebar or upload your first Markdown, TXT, or JSON file here."}
                    </p>
                  </div>
                ) : (
                  visible.map(file => {
                    const isSelected = file.key === selected?.key;
                    const ext = file.name.includes(".") ? file.name.split(".").pop()?.toUpperCase() : "FILE";
                    return (
                      <div
                        key={file.key}
                        role="row"
                        className={`${styles.figmaTableRow} ${isSelected ? styles.figmaTableRowSelected : ""}`}
                      >
                        <div className={styles.colCheck} role="cell">
                          <button
                            type="button"
                            className={`${styles.checkboxBtn} ${isSelected ? styles.checkboxBtnChecked : ""}`}
                            aria-label={`Select ${file.name}`}
                            aria-pressed={isSelected}
                            onClick={() => setSelectedKey(isSelected ? null : file.key)}
                          >
                            {isSelected && <DesignIcon name="library-Check" />}
                          </button>
                        </div>

                        <div className={styles.colFile} role="cell">
                          <div className={styles.fileIdentity}>
                            <DesignIcon name="library-FileText" />
                            <div className={styles.fileIdentityText}>
                              <Link href={documentHref("details", file.key)} className={styles.fileIdentityTitle}>
                                {file.name}
                              </Link>
                              <span className={styles.fileIdentitySub}>
                                {fileFolderLabel(root, file.key)} · {file.key}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className={styles.colFormat} role="cell">
                          <div className={styles.cellStack}>
                            <span className={styles.cellPrimary}>{ext}</span>
                            <span className={styles.cellSecondary}>{formatFileSize(file.size)}</span>
                          </div>
                        </div>

                        <div className={styles.colUpdated} role="cell">
                          <div className={styles.cellStack}>
                            <time dateTime={file.lastModified} className={styles.cellPrimary}>
                              {formatFigmaDate(file.lastModified)}
                            </time>
                            <span className={styles.cellSecondary}>R2 storage (UTC)</span>
                          </div>
                        </div>

                        <div className={styles.colReview} role="cell">
                          <Tooltip title={advancedUnavailable}>
                            <span className={styles.badges}>Unavailable</span>
                          </Tooltip>
                        </div>

                        <div className={styles.colIngestion} role="cell">
                          <Tooltip title={advancedUnavailable}>
                            <span className={styles.badges}>Not run</span>
                          </Tooltip>
                        </div>

                        <div className={styles.colActions} role="cell">
                          <div className={styles.rowActions}>
                            <Link href={documentHref("details", file.key)} className={styles.rowActionLink}>
                              View
                            </Link>
                            <button
                              type="button"
                              className={styles.rowActionLink}
                              onClick={() => void download(file)}
                            >
                              Download
                            </button>
                            <Dropdown
                              menu={{
                                items: [
                                  {
                                    key: "metadata",
                                    label: "Edit metadata",
                                    onClick: () => router.push(documentHref("metadata", file.key)),
                                  },
                                  {
                                    key: "replace",
                                    label: "Replace (unavailable)",
                                    disabled: true,
                                  },
                                  {
                                    key: "delete",
                                    label: "Delete file",
                                    danger: true,
                                    onClick: () => setDeleting(file),
                                  },
                                ],
                              }}
                            >
                              <button
                                type="button"
                                className={styles.rowActionLink}
                                aria-label={`More actions for ${file.name}`}
                              >
                                More
                              </button>
                            </Dropdown>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              <div className={styles.pagination}>
                <span className={styles.muted}>
                  Showing {visible.length} of {filtered.length} loaded documents · All times UTC
                </span>
                <div className={styles.actions}>
                  <span className={styles.muted}>
                    Page {shownPage} of {totalPages}{listing.page?.nextContinuationToken ? "+" : ""}
                  </span>
                  <button
                    type="button"
                    className={styles.figmaBtn}
                    disabled={shownPage <= 1}
                    onClick={() => setPage(n => n - 1)}
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    className={styles.figmaBtn}
                    disabled={
                      listing.more ||
                      (shownPage * pageSize >= filtered.length && !listing.page?.nextContinuationToken)
                    }
                    onClick={() => {
                      if (shownPage * pageSize < filtered.length) setPage(n => n + 1);
                      else void listing.loadMore();
                    }}
                  >
                    {listing.more
                      ? "Loading…"
                      : shownPage * pageSize < filtered.length
                      ? "Next"
                      : listing.page?.nextContinuationToken
                      ? "Load more"
                      : "Next"}
                  </button>
                </div>
              </div>
            </>
          )}

          <div className={styles.panel}>
            <div className={styles.replacementHeader}>
              <div className={styles.panelHeading} style={{ flex: 1 }}>
                <h2>Replace original file</h2>
                <p>
                  {selected
                    ? `${selected.name} · ${formatFileSize(selected.size)} · ${fileFolderLabel(root, selected.key)}`
                    : "Select a document row above to inspect replacement options."}
                </p>
              </div>
              <Tooltip title="The backend enforces immutable keys and does not expose a versioned replacement API.">
                <button type="button" className={styles.figmaBtn} disabled>
                  Choose replacement file
                </button>
              </Tooltip>
            </div>
            <p className={styles.muted}>
              A replacement requires a versioned revision contract. The current R2 upload contract rejects duplicate filenames (HTTP 409) to protect existing objects.
            </p>
          </div>

          <div className={styles.notice}>
            <DesignIcon name="library-Info" />
            <div className={styles.noticeBody}>
              <p>
                Upload supports multiple Markdown (.md), TXT (.txt), or JSON (.json) files. New uploads are stored in Cloudflare R2 (<code>knowledge-heritage</code>) only; they are not available to the chatbot until review and ingestion endpoints are connected.
              </p>
            </div>
          </div>
        </div>
      </div>

      <CreateFolderDialog
        prefix={listing.prefix}
        open={createOpen}
        close={() => setCreateOpen(false)}
        created={listing.refresh}
      />
      <UploadDocumentsModal
        prefix={listing.prefix}
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
      />
      <DeleteFileDialog
        file={deleting}
        close={() => setDeleting(null)}
        deleted={listing.refresh}
      />
    </section>
  );
}
