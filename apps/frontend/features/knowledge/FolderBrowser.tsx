"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Button, Tree, type TreeProps } from "antd";
import { isAborted, knowledgeApi, knowledgeError } from "../../services/knowledge.service";
import { appendKnowledgePage, breadcrumbParts, libraryHref, readKnowledgePage } from "./folder-state";
import { useKnowledge } from "./KnowledgeProvider";
import { DesignIcon } from "./DesignIcon";
import styles from "./knowledge.module.css";

export function KnowledgeBreadcrumbs({ prefix, current }: { prefix: string; current?: string }) {
  const { root } = useKnowledge();
  const parts = breadcrumbParts(root, prefix);
  return <nav className={styles.breadcrumbs} aria-label="Folder breadcrumbs">
    <Link href={libraryHref()}>Cloudflare R2</Link><DesignIcon name="library-ChevronRight" />
    <Link href={libraryHref()} aria-current={!parts.length && !current ? "page" : undefined}>All documents</Link>
    {parts.map((part, index) => <span key={part.prefix} className={styles.crumbPart}>
      <DesignIcon name="library-ChevronRight" /><Link href={libraryHref(part.prefix)} aria-current={index === parts.length - 1 && !current ? "page" : undefined}>{part.label}</Link>
    </span>)}
    {current && <span className={styles.crumbPart}><DesignIcon name="library-ChevronRight" /><span aria-current="page">{current}</span></span>}
  </nav>;
}

export function FolderBrowser({ prefix, onSelect }: { prefix: string; onSelect: (prefix: string) => void }) {
  const { root, folderPages, remember } = useKnowledge();
  const [expanded, setExpanded] = useState<string[]>([root]);
  const [error, setError] = useState("");
  const [loadingMore, setLoadingMore] = useState(false);
  const controllers = useRef(new Set<AbortController>());
  useEffect(() => () => { for (const controller of controllers.current) controller.abort(); }, []);
  useEffect(() => { setExpanded(keys => Array.from(new Set([...keys, root, ...breadcrumbParts(root, prefix).map(p => p.prefix)]))); }, [prefix, root]);

  async function load(folder: string, more = false) {
    const existing = folderPages[folder];
    if (existing && !more) return;
    const controller = new AbortController(); controllers.current.add(controller);
    try {
      setError("");
      const page = await readKnowledgePage(knowledgeApi, folder, more ? existing?.nextContinuationToken ?? undefined : undefined, controller.signal);
      if (!controller.signal.aborted) remember(more && existing ? appendKnowledgePage(existing, page) : page);
    } catch (e) { if (!isAborted(e) && !controller.signal.aborted) setError(knowledgeError(e)); }
    finally { controllers.current.delete(controller); }
  }
  function children(folder: string, depth = 0): NonNullable<TreeProps["treeData"]> {
    if (depth > 40) return [];
    return (folderPages[folder]?.folders ?? []).filter(row => row.prefix.startsWith(folder) && row.prefix !== folder).map(row => ({
      key: row.prefix, title: row.name, icon: <DesignIcon name={row.prefix === prefix ? "library-FolderOpen" : "library-Folder"} />,
      isLeaf: folderPages[row.prefix] ? !folderPages[row.prefix].folders.length && !folderPages[row.prefix].nextContinuationToken : false,
      children: folderPages[row.prefix] ? children(row.prefix, depth + 1) : undefined,
    }));
  }
  return <aside className={styles.folderBrowser} aria-label="R2 folders">
    <div className={styles.storageHeading}><DesignIcon name="library-Database" />Cloudflare R2</div>
    <div className={styles.bucket}>knowledge-heritage</div>
    <Tree className={styles.folderTree} showIcon blockNode selectedKeys={[prefix]} expandedKeys={expanded}
      onExpand={keys => setExpanded(keys.map(String))} loadData={node => load(String(node.key))}
      switcherIcon={<DesignIcon name="library-ChevronRight" />}
      onSelect={keys => { if (keys.length) onSelect(String(keys[0])); }}
      treeData={[{ key: root, title: "All documents", icon: <DesignIcon name="library-FolderOpen" />, children: children(root) }]} />
    {folderPages[prefix]?.nextContinuationToken && <Button size="small" loading={loadingMore} onClick={async () => {
      setLoadingMore(true); await load(prefix, true); setLoadingMore(false);
    }}>Load more folder entries</Button>}
    {error && <div role="alert" className={styles.error}><p>{error}</p><Button size="small" onClick={() => void load(prefix)}>Retry folders</Button></div>}
    <p className={styles.treeNote}>Folders organize stored files. They do not change review or ingestion status.</p>
    {root && <p className={styles.treeNote}>Library scope: {root}</p>}
  </aside>;
}
