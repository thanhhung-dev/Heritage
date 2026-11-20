"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { App, Button, Dropdown, Input, Select, Table, Tooltip, type TableColumnsType } from "antd";
import { knowledgeError } from "../../services/knowledge.service";
import { DesignIcon } from "./DesignIcon";
import { FolderBrowser, KnowledgeBreadcrumbs } from "./FolderBrowser";
import { CreateFolderDialog, DeleteFileDialog } from "./FileDialogs";
import { UploadDocumentsModal } from "./UploadModal";
import { documentHref, libraryHref, uploadHref } from "./folder-state";
import { formatFileSize } from "./file-policy";
import { KnowledgeFeedback } from "./KnowledgeFeedback";
import { downloadKnowledgeFile } from "./knowledge-actions";
import { useKnowledgeFolder } from "./useKnowledgeFolder";
import type { KnowledgeFile } from "./types";
import styles from "./knowledge.module.css";

const pageSize = 10;
const advancedUnavailable = "The backend does not expose review or ingestion states for these files.";
export function DocumentLibrary() {
  const query = useSearchParams(), router = useRouter(), { message } = App.useApp();
  const listing = useKnowledgeFolder(query.has("prefix") ? query.get("prefix")! : undefined);
  const [search, setSearch] = useState(""); const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false); const [uploadOpen, setUploadOpen] = useState(false); const [deleting, setDeleting] = useState<KnowledgeFile | null>(null);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  useEffect(() => { setPage(1); setSearch(""); setSelectedKey(null); }, [listing.prefix]);
  const files = listing.page?.files;
  const filtered = useMemo(() => (files ?? []).filter(file => file.name.toLocaleLowerCase().includes(search.toLocaleLowerCase())), [files, search]);
  const selected = files?.find(file => file.key === selectedKey);
  const shownPage = Math.min(page, Math.max(1, Math.ceil(filtered.length / pageSize)));
  const visible = filtered.slice((shownPage - 1) * pageSize, shownPage * pageSize);
  async function download(file: KnowledgeFile) {
    try { await downloadKnowledgeFile(file.key); } catch (e) { void message.error(knowledgeError(e)); }
  }
  const columns: TableColumnsType<KnowledgeFile> = [
    { title: "File name", key: "name", width: 290, render: (_value, file) => <div className={styles.fileIdentity}>
      <DesignIcon name="library-FileText" /><div><Link href={documentHref("details", file.key)}>{file.name}</Link><p className={styles.muted}>{file.key}</p></div>
    </div> },
    { title: "Format / size", key: "format", width: 110, render: (_value, file) => <><span>{file.name.includes(".") ? file.name.split(".").pop()?.toUpperCase() : "FILE"}</span><p className={styles.muted}>{formatFileSize(file.size)}</p></> },
    { title: "Updated", dataIndex: "lastModified", width: 160, render: (value: string) => <><time dateTime={value}>{new Date(value).toLocaleString("en-GB", { timeZone: "UTC", dateStyle: "medium", timeStyle: "short" })}</time><p className={styles.muted}>UTC</p></> },
    { title: "Review", key: "review", width: 115, render: () => <Tooltip title={advancedUnavailable}><span className={styles.badges}>Unavailable</span></Tooltip> },
    { title: "Ingestion", key: "ingestion", width: 115, render: () => <Tooltip title={advancedUnavailable}><span className={styles.badges}>Unavailable</span></Tooltip> },
    { title: "Actions", key: "actions", width: 220, render: (_value, file) => <div className={styles.rowActions}>
      <Link href={documentHref("details", file.key)}>View</Link><Button type="text" size="small" onClick={() => void download(file)}>Download</Button>
      <Dropdown menu={{ items: [
        { key: "metadata", label: "Document metadata", onClick: () => router.push(documentHref("metadata", file.key)) },
        { key: "replace", label: "Replace file (unavailable)", disabled: true },
        { key: "delete", label: "Delete file", danger: true, onClick: () => setDeleting(file) },
      ] }}><Button type="text" size="small" aria-label={`More actions for ${file.name}`}>More</Button></Dropdown>
    </div> },
  ];
  return <section className={styles.page} aria-label="Document library">
    <header className={styles.header}><div><h1>Document library</h1><p>Manage original files, metadata, review status, and ingestion in one place.</p></div>
      <div className={styles.actions}><Button disabled={listing.loading || Boolean(listing.error)} onClick={() => setCreateOpen(true)}>Create folder</Button>
        <Link href={uploadHref(listing.prefix)}><Button>Upload workspace</Button></Link>
        <Button type="primary" disabled={listing.loading || Boolean(listing.error)} onClick={() => setUploadOpen(true)}>Upload documents</Button></div>
    </header>
    <div className={styles.workspace}>
      <FolderBrowser prefix={listing.prefix} onSelect={prefix => router.push(libraryHref(prefix))} />
      <div className={styles.mainColumn}>
        <KnowledgeBreadcrumbs prefix={listing.prefix} />
        <div className={styles.toolbar}><Input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} placeholder="Search loaded file names…" aria-label="Search loaded files" allowClear />
          <Tooltip title={advancedUnavailable}><Select disabled value="unavailable" aria-label="Review filter unavailable" options={[{ value: "unavailable", label: "Review: Unavailable" }]} /></Tooltip>
          <Tooltip title={advancedUnavailable}><Select disabled value="unavailable" aria-label="Ingestion filter unavailable" options={[{ value: "unavailable", label: "Ingestion: Unavailable" }]} /></Tooltip>
        </div>
        <p className={styles.resultsNote}>{files?.length ?? 0} files loaded · Search applies to loaded files only</p>
        {listing.loading ? <KnowledgeFeedback loading /> : listing.error ? <KnowledgeFeedback error={listing.error} retry={listing.refresh} /> : <>
          <Table<KnowledgeFile> className={styles.fileTable} size="small" columns={columns} dataSource={visible} rowKey="key" pagination={false} scroll={{ x: 1040 }}
            rowSelection={{ selectedRowKeys: selectedKey ? [selectedKey] : [], hideSelectAll: true,
              onChange: keys => setSelectedKey(keys.length ? String(keys.at(-1)) : null),
              getCheckboxProps: file => ({ "aria-label": `Select ${file.name}` }) }}
            locale={{ emptyText: <div className={styles.empty}><DesignIcon name="library-FolderOpen" /><h2>{search ? "No matching files" : "No files in this folder"}</h2><p>{search ? "Try another name or load more records." : "Open a folder from the sidebar or upload your first file here."}</p></div> }} />
          <div className={styles.pagination}><span className={styles.muted}>Showing {visible.length ? (shownPage - 1) * pageSize + 1 : 0}–{Math.min(shownPage * pageSize, filtered.length)} of {filtered.length} loaded matches · All times UTC</span>
            <div className={styles.actions}><span className={styles.muted}>Page {shownPage}</span><Button disabled={shownPage <= 1} onClick={() => setPage(n => n - 1)}>Previous</Button>
              <Button loading={listing.more} disabled={shownPage * pageSize >= filtered.length && !listing.page?.nextContinuationToken} onClick={() => {
                if (shownPage * pageSize < filtered.length) setPage(n => n + 1); else void listing.loadMore();
              }}>{shownPage * pageSize < filtered.length ? "Next" : listing.page?.nextContinuationToken ? "Load more" : "Next"}</Button></div>
          </div>
        </>}
        <div className={styles.panel}><div className={styles.replacementHeader}><div><h2>Replace original file</h2><p className={styles.muted}>{selected ? `${selected.name} · ${formatFileSize(selected.size)}` : "Select a file to inspect replacement options."}</p></div><Button disabled>Choose replacement file</Button></div><p className={styles.treeNote}>Versioned replacement is not available in the current backend. Existing filenames cannot be overwritten.</p></div>
        <div className={styles.notice}><DesignIcon name="library-Info" /><p>Upload supports Markdown, TXT and JSON. Completion means stored in R2 only. Review and ingestion are separate and are not currently available for these files.</p></div>
      </div>
    </div>
    <CreateFolderDialog prefix={listing.prefix} open={createOpen} close={() => setCreateOpen(false)} created={listing.refresh} />
    <UploadDocumentsModal prefix={listing.prefix} open={uploadOpen} onClose={() => setUploadOpen(false)} />
    <DeleteFileDialog file={deleting} close={() => setDeleting(null)} deleted={listing.refresh} />
  </section>;
}
