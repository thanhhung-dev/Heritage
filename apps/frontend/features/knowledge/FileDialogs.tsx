"use client";

import { useEffect, useRef, useState } from "react";
import { Button, Input, Modal } from "antd";
import { ApiError } from "../../lib/api";
import { knowledgeApi, knowledgeError } from "../../services/knowledge.service";
import type { KnowledgeFile } from "./types";
import styles from "./knowledge.module.css";

export function CreateFolderDialog({ prefix, open, close, created }: { prefix: string; open: boolean; close: () => void; created: () => void }) {
  const [name, setName] = useState(""); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  useEffect(() => { if (open) { setName(""); setError(""); } }, [open, prefix]);
  async function submit() {
    if (lock.current) return;
    if (!name.trim()) { setError("Enter a folder name."); return; }
    lock.current = true; setBusy(true); setError("");
    try { await knowledgeApi.createFolder(prefix, name); setName(""); created(); close(); }
    catch (e) { setError(knowledgeError(e)); }
    finally { lock.current = false; setBusy(false); }
  }
  return <Modal title="Create folder" open={open} onCancel={() => { if (!busy) close(); }} footer={null} className={styles.dialog} destroyOnHidden maskClosable={!busy} closable={!busy}>
    <form onSubmit={e => { e.preventDefault(); void submit(); }}>
      <p className={styles.dialogDescription}>Create a logical folder in {prefix || "the library root"}.</p>
      <label htmlFor="knowledge-folder-name">Folder name</label>
      <Input autoFocus id="knowledge-folder-name" value={name} onChange={e => setName(e.target.value)} disabled={busy} maxLength={255} />
      {error && <p className={styles.formError} role="alert">{error}</p>}
      <div className={styles.dialogFooter}><Button disabled={busy} onClick={close}>Cancel</Button><Button type="primary" htmlType="submit" loading={busy}>Create folder</Button></div>
    </form>
  </Modal>;
}

export function DeleteFileDialog({ file, close, deleted }: { file: KnowledgeFile | null; close: () => void; deleted: () => void }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const lock = useRef(false);
  useEffect(() => { setError(""); }, [file?.key]);
  async function remove() {
    if (!file || lock.current) return;
    lock.current = true; setBusy(true); setError("");
    try { await knowledgeApi.deleteObject(file.key); deleted(); close(); }
    catch (e) {
      if (e instanceof ApiError && e.status === 404) { deleted(); close(); }
      else setError(knowledgeError(e));
    } finally { lock.current = false; setBusy(false); }
  }
  return <Modal title="Delete this file?" open={Boolean(file)} onCancel={() => { if (!busy) close(); }} footer={null} className={styles.dialog} destroyOnHidden maskClosable={!busy} closable={!busy}>
    <p className={styles.dialogDescription}>Delete only this original file from R2. This cannot be undone.</p>
    <strong>{file?.name}</strong><code className={styles.exactKey}>{file?.key}</code>
    <p className={styles.muted}>Other files and folders will be kept.</p>
    {error && <p className={styles.formError} role="alert">{error}</p>}
    <div className={styles.dialogFooter}><Button disabled={busy} onClick={close}>Cancel</Button><Button danger type="primary" loading={busy} onClick={() => void remove()}>Delete file</Button></div>
  </Modal>;
}
