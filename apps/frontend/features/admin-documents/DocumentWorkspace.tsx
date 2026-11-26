"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { Button, Input, Modal, Select, Table, Upload, message } from "antd";
import { addDocument, getDocuments, resetDocuments, subscribeDocuments, updateDocument, type DocumentRecord } from "./mock-documents";
import styles from "./documents.module.css";

type View = "library" | "upload" | "edit" | "details";
const folders = ["All documents", "Vietnam", "Vietnam / Central", "Vietnam / Northern", "Vietnam / Southern", "Drafts"];
const reviews = ["Draft", "Pending review", "Approved", "Changes requested"];
const ingestions = ["Not run", "Indexed", "Processing", "Failed"];
const allowed = /\.(pdf|docx|txt|csv)$/i;
const formatSize = (n: number) => n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.ceil(n / 1024)} KB`;
const initialServer: DocumentRecord[] = [];

export function DocumentWorkspace() {
  const records = useSyncExternalStore(subscribeDocuments, getDocuments, () => initialServer);
  const [view, setView] = useState<View>("library");
  const [id, setId] = useState("");
  const [folder, setFolder] = useState("All documents");
  const [query, setQuery] = useState("");
  const [review, setReview] = useState("All");
  const [ingestion, setIngestion] = useState("All");
  const [selected, setSelected] = useState<string[]>([]);
  const [modal, setModal] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [queue, setQueue] = useState<string[]>([]);
  const [queueState, setQueueState] = useState<Record<string, string>>({});
  const [form, setForm] = useState({ title: "", region: "", documentType: "", sourceUrl: "" });
  const [errors, setErrors] = useState<string[]>([]);
  const [notice, setNotice] = useState("");
  const [page, setPage] = useState(1);
  const fileInput = useRef<HTMLInputElement>(null);
  const record = records.find((item) => item.id === id);
  const filtered = records.filter((item) => (folder === "All documents" || item.folder === folder || item.folder.startsWith(`${folder} /`)) && item.filename.toLowerCase().includes(query.toLowerCase()) && (review === "All" || item.review === review) && (ingestion === "All" || item.ingestion === ingestion));
  useEffect(() => { setPage(1); }, [folder, query, review, ingestion]);
  useEffect(() => { const reset = () => { resetDocuments(); setFiles([]); }; window.addEventListener("storage", reset); return () => window.removeEventListener("storage", reset); }, []);
  const open = (item: DocumentRecord, target: View) => { setId(item.id); setForm({ title: item.title, region: item.region, documentType: item.documentType, sourceUrl: item.sourceUrl }); setErrors([]); setView(target); };
  const chooseFiles = (picked: File[]) => {
    const valid = picked.filter((file) => allowed.test(file.name) && file.size > 0);
    if (valid.length !== picked.length) message.error("Choose non-empty PDF, DOCX, TXT, or CSV files.");
    setFiles((current) => [...current, ...valid]);
  };
  const upload = () => {
    if (!files.length) return;
    const ids = files.map((file) => addDocument(file, folder === "All documents" ? "Drafts" : folder));
    setQueue(ids); setQueueState(Object.fromEntries(ids.map((key) => [key, "Completed (demo)"]))); setFiles([]); setModal(false); setView("upload");
  };
  const save = (submit: boolean) => {
    if (!record) return;
    const missing = submit ? [!form.title.trim() && "title", !form.region && "region", !form.documentType && "documentType", !form.sourceUrl.trim() && "sourceUrl"].filter(Boolean) as string[] : [];
    if (form.sourceUrl.trim()) { try { const url = new URL(form.sourceUrl); if (!/^https?:$/.test(url.protocol)) throw new Error(); } catch { missing.push("sourceUrl"); } }
    setErrors(missing);
    if (missing.length) return;
    updateDocument(record.id, { ...form, review: submit ? "Pending review" : "Draft" });
    setNotice(submit ? "Submitted for review in this demo only." : "Draft saved in this demo session only."); setView("details");
  };
  const download = () => { if (!record?.file) return; const url = URL.createObjectURL(record.file); const a = document.createElement("a"); a.href = url; a.download = record.filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); };
  const replace = (file: File) => { if (!record) return; if (!allowed.test(file.name) || !file.size) { message.error("Choose a non-empty PDF, DOCX, TXT, or CSV file."); return; } updateDocument(record.id, { file, filename: file.name, size: file.size, format: file.name.split(".").pop()?.toUpperCase() ?? "", revision: record.revision + 1, review: "Draft" }); setNotice("Replacement simulated in this session only."); };
  const columns = [
    { title: "File name", key: "name", render: (_: unknown, item: DocumentRecord) => <><strong>{item.filename}</strong><div className={styles.muted}>{item.folder}</div></> },
    { title: "Format / size", key: "size", render: (_: unknown, item: DocumentRecord) => <>{item.format}<div className={styles.muted}>{formatSize(item.size)}</div></> },
    { title: "Updated / uploaded by", key: "updated", render: (_: unknown, item: DocumentRecord) => <>{item.updated}<div className={styles.muted}>{item.uploader}</div></> },
    { title: "Review", dataIndex: "review" }, { title: "Ingestion", dataIndex: "ingestion" },
    { title: "Actions", key: "actions", render: (_: unknown, item: DocumentRecord) => <div className={styles.actions}><Button type="link" onClick={() => open(item, "details")}>{item.review === "Pending review" ? "Review" : "View"}</Button><Button type="link" disabled={!item.file} onClick={() => { open(item, "details"); message.info("Use Download file on the details page."); }}>Download</Button><Button type="link" onClick={() => { setId(item.id); fileInput.current?.click(); }}>Replace</Button></div> },
  ];
  return <div className={styles.workspace}>
    <input ref={fileInput} type="file" accept=".pdf,.docx,.txt,.csv" hidden onChange={(event) => { const file = event.target.files?.[0]; const target = records.find((item) => item.id === id); if (file && target) { if (!allowed.test(file.name) || !file.size) message.error("Choose a non-empty PDF, DOCX, TXT, or CSV file."); else { updateDocument(target.id, { file, filename: file.name, size: file.size, format: file.name.split(".").pop()?.toUpperCase() ?? "", revision: target.revision + 1, review: "Draft" }); message.success("Replacement simulated in this session only."); } } event.currentTarget.value = ""; }} />
    <header className={styles.header}><div><h1>{view === "library" ? "Document library" : view === "upload" ? "Upload documents" : view === "edit" ? "Edit document metadata" : "Document details"}</h1><p>{view === "library" ? "Manage original files, metadata, review status, and ingestion in one place." : record?.filename ?? "Preview documents and metadata."}</p></div><div className={styles.actions}>{view === "library" ? <><Button disabled title="Not available in this demo">Create folder</Button><Button type="primary" onClick={() => setModal(true)}>Upload documents</Button></> : <Button onClick={() => setView("library")}>Back to library</Button>}</div></header>
    <div className={styles.demo}><strong>DEMO DATA</strong> · Preview only · Changes stay in this tab and are not saved to a server.</div>
    {notice && <p role="status">{notice}</p>}
    {view === "library" && <div className={styles.library}><aside className={styles.folders}><strong>Cloudflare R2</strong><p className={styles.muted}>heritage-documents-demo</p>{folders.map((name) => <button className={folder === name ? styles.active : ""} key={name} onClick={() => setFolder(name)}>{name}<span>{name === "All documents" ? records.length : records.filter((r) => r.folder === name || r.folder.startsWith(`${name} /`)).length}</span></button>)}</aside><section className={styles.content}><p>Cloudflare R2　›　{folder}</p><div className={styles.filters}><Input placeholder="Search file names..." aria-label="Search file names" value={query} onChange={(e) => setQuery(e.target.value)} /><Select aria-label="Review status" value={review} onChange={setReview} options={["All", ...reviews].map((value) => ({ value, label: `Review: ${value}` }))} /><Select aria-label="Ingestion status" value={ingestion} onChange={setIngestion} options={["All", ...ingestions].map((value) => ({ value, label: `Ingestion: ${value}` }))} /><span className={styles.muted}>{filtered.length} documents</span></div><Table rowKey="id" columns={columns} dataSource={filtered} rowSelection={{ selectedRowKeys: selected, onChange: (keys) => setSelected(keys.map(String)) }} pagination={{ current: page, pageSize: 10, onChange: setPage, showSizeChanger: false }} scroll={{ x: 850 }} locale={{ emptyText: "No documents found" }} /><div className={styles.box}><strong>Replace original file</strong><p className={styles.muted}>{selected.length === 1 ? records.find((r) => r.id === selected[0])?.filename : "Select one document to replace."}</p><Button disabled={selected.length !== 1} onClick={() => { setId(selected[0]); fileInput.current?.click(); }}>Choose replacement file</Button><p className={styles.muted}>Replacement is simulated and returns the document to Draft.</p></div></section></div>}
    {view === "upload" && <section><div className={styles.box}><p>Destination: {folder === "All documents" ? "Drafts" : folder}</p><Upload.Dragger multiple accept=".pdf,.docx,.txt,.csv" showUploadList={false} beforeUpload={(file) => { chooseFiles([file]); return Upload.LIST_IGNORE; }}><p>Drag and drop documents here</p><p className={styles.muted}>Select multiple PDF, DOCX, TXT, or CSV files.</p><Button>Choose files</Button></Upload.Dragger>{files.length > 0 && <Button onClick={upload}>Add {files.length} files to demo queue</Button>}</div><h2>Upload queue</h2>{queue.map((key) => { const item = records.find((r) => r.id === key); return item && <div className={styles.queue} key={key}><span>{item.filename} · {formatSize(item.size)}</span><span>{queueState[key]}</span><Button onClick={() => open(item, "edit")}>Edit metadata</Button><Button onClick={() => setQueueState((old) => ({ ...old, [key]: old[key]?.startsWith("Cancelled") ? "Completed (demo)" : "Cancelled (demo)" }))}>{queueState[key]?.startsWith("Cancelled") ? "Retry upload" : "Cancel upload"}</Button></div>; })}<p className={styles.muted}>Demo only: files are not sent to storage.</p>{queue[0] && <Button type="primary" onClick={() => { const item = records.find((r) => r.id === queue[0]); if (item) open(item, "edit"); }}>Continue to metadata</Button>}</section>}
    {(view === "details" || view === "edit") && !record && <div className={styles.box}>Document not found. <Button onClick={() => setView("library")}>Back to library</Button></div>}
    {record && (view === "details" || view === "edit") && <><div className={styles.statuses}><div><span>Storage</span><strong>Demo only</strong></div><div><span>Review</span><strong>{record.review}</strong></div><div><span>Ingestion</span><strong>{record.ingestion}</strong></div></div>{view === "edit" ? <div className={styles.twoColumns}><section className={styles.box}><h2>Document metadata</h2><p className={styles.muted}>Fields marked * are required to submit this revision for review.</p>{([['title','Document title'],['region','Region'],['documentType','Document type'],['sourceUrl','Citation source URL']] as const).map(([key,label]) => <label className={styles.field} key={key}>{label} *<Input value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} aria-invalid={errors.includes(key)} />{errors.includes(key) && <span role="alert" className={styles.error}>{key === 'sourceUrl' ? 'Enter a valid HTTP or HTTPS URL.' : 'This field is required.'}</span>}</label>)}<div className={styles.actions}><Button onClick={() => setView("library")}>Cancel</Button><Button onClick={() => save(false)}>Save draft</Button><Button type="primary" onClick={() => save(true)}>Submit for review</Button></div></section><aside className={styles.box}><h2>Original file</h2><p>{record.filename}</p><p>{record.format} · {formatSize(record.size)}</p><p className={styles.muted}>Demo only. Permissions are enforced by the backend.</p></aside></div> : <div className={styles.twoColumns}><section className={styles.box}><h2>Extracted text</h2><p className={styles.muted}>Preview only · illustrative content</p><p>No extracted text is available for this demo document.</p><h2>Chunks</h2><p className={styles.muted}>No chunks available in this demo.</p></section><aside className={styles.box}><h2>Metadata and original file</h2><p><strong>Title</strong><br />{record.title}</p><p><strong>Region</strong><br />{record.region || "—"}</p><p><strong>Document type</strong><br />{record.documentType || "—"}</p><p><strong>Citation source URL</strong><br />{record.sourceUrl || "—"}</p><p>{record.filename} · {formatSize(record.size)}</p><div className={styles.actions}><Button onClick={() => open(record, "edit")}>Edit metadata</Button><Button disabled={!record.file} onClick={download}>Download file</Button><Button onClick={() => fileInput.current?.click()}>Replace file</Button></div>{record.ingestion === "Failed" && <p><Button disabled title="Ingestion is not connected">Retry ingestion</Button></p>}</aside></div>}</>}
    <Modal title="Upload documents" open={modal} onCancel={() => setModal(false)} onOk={upload} okText={`Upload ${files.length || ""} files`} okButtonProps={{ disabled: !files.length }} destroyOnHidden><p>Demo only. Files are not stored on a server.</p><label className={styles.field}>Destination<Select value={folder === "All documents" ? "Drafts" : folder} onChange={setFolder} options={folders.filter((f) => f !== "All documents").map((value) => ({ value }))} /></label><Upload.Dragger multiple accept=".pdf,.docx,.txt,.csv" showUploadList={false} beforeUpload={(file) => { chooseFiles([file]); return Upload.LIST_IGNORE; }}><p>Drag and drop documents here</p><p>Select multiple PDF, DOCX, TXT, or CSV files.</p><Button>Browse files</Button></Upload.Dragger><h3>Selected files ({files.length})</h3>{files.map((file, index) => <div className={styles.queue} key={`${file.name}-${index}`}><span>{file.name} · {formatSize(file.size)}</span><Button aria-label={`Remove ${file.name}`} onClick={() => setFiles((old) => old.filter((_, i) => i !== index))}>Remove</Button></div>)}</Modal>
  </div>;
}

