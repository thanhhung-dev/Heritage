"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ApiError } from "../../lib/api";
import { isAborted, knowledgeApi } from "../../services/knowledge.service";
import { readKnowledgePage } from "./folder-state";
import { KnowledgeFeedback } from "./KnowledgeFeedback";
import { KnowledgeUploadQueue } from "./upload-queue";
import { uploadDirect } from "./upload-transport";
import { useAdminSession } from "./useAdminSession";
import type { KnowledgePage } from "./types";
import styles from "./knowledge.module.css";

interface LibraryContext {
  root: string;
  queue: KnowledgeUploadQueue | null;
  revision: number;
  folderPages: Readonly<Record<string, KnowledgePage>>;
  remember: (page: KnowledgePage) => void;
  takeRootSeed: (prefix: string) => KnowledgePage | null;
}
const Context = createContext<LibraryContext | null>(null);

export function KnowledgeProvider({ children }: { children: ReactNode }) {
  const session = useAdminSession();
  const [rootPage, setRootPage] = useState<KnowledgePage | null>(null);
  const [rootError, setRootError] = useState<unknown>();
  const [rootAttempt, setRootAttempt] = useState(0);
  const [revision, setRevision] = useState(0);
  const [queue, setQueue] = useState<KnowledgeUploadQueue | null>(null);
  const [folderPages, setFolderPages] = useState<Record<string, KnowledgePage>>({});
  const seed = useRef<KnowledgePage | null>(null);
  const remember = useCallback((page: KnowledgePage) => setFolderPages(previous => ({ ...previous, [page.prefix]: page })), []);
  const takeRootSeed = useCallback((prefix: string) => {
    if (seed.current?.prefix !== prefix) return null;
    const page = seed.current; seed.current = null; return page;
  }, []);

  useEffect(() => {
    setRootPage(null); setRootError(undefined); setFolderPages({}); seed.current = null;
    if (session.status !== "ready") return;
    const controller = new AbortController();
    void readKnowledgePage(knowledgeApi, undefined, undefined, controller.signal).then(page => {
      if (controller.signal.aborted) return;
      seed.current = page; setRootPage(page); remember(page);
    }).catch(error => { if (!isAborted(error) && !controller.signal.aborted) setRootError(error); });
    return () => controller.abort();
  }, [session.status, session.user?.account_id, rootAttempt, remember]);

  useEffect(() => {
    if (session.status !== "ready") { setQueue(null); return; }
    // Construct inside the effect so React Strict Mode gets a fresh controller
    // after its development-only setup/cleanup cycle.
    const current = new KnowledgeUploadQueue(knowledgeApi, uploadDirect, { onStored: () => setRevision(value => value + 1) });
    setQueue(current);
    return () => current.dispose();
  }, [session.status, session.user?.account_id]);

  const context = useMemo<LibraryContext | null>(() => rootPage ? {
    root: rootPage.prefix, queue, revision, folderPages, remember, takeRootSeed,
  } : null, [rootPage, queue, revision, folderPages, remember, takeRootSeed]);
  if (session.status === "checking") return <section className={styles.page}><KnowledgeFeedback loading /></section>;
  if (session.status !== "ready") return <section className={styles.page}><KnowledgeFeedback error={new ApiError("Administrator access required.", session.status === "anonymous" ? 401 : 403)} /></section>;
  if (rootError) return <section className={styles.page}><KnowledgeFeedback error={rootError} retry={() => setRootAttempt(n => n + 1)} /></section>;
  if (!context) return <section className={styles.page}><KnowledgeFeedback loading /></section>;
  return <Context.Provider value={context}>{children}</Context.Provider>;
}

export function useKnowledge() {
  const value = useContext(Context);
  if (!value) throw new Error("Knowledge components must be inside KnowledgeProvider");
  return value;
}
