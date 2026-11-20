"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { isAborted, knowledgeApi, knowledgeError } from "../../services/knowledge.service";
import { appendKnowledgePage, breadcrumbParts, libraryHref, readKnowledgePage } from "./folder-state";
import { useKnowledge } from "./KnowledgeProvider";
import { DesignIcon } from "./DesignIcon";
import styles from "./knowledge.module.css";

export function KnowledgeBreadcrumbs({ prefix, current }: { prefix: string; current?: string }) {
  const { root } = useKnowledge();
  const parts = breadcrumbParts(root, prefix);
  return (
    <nav className={styles.breadcrumbs} aria-label="Folder breadcrumbs">
      <Link href={libraryHref()}>Cloudflare R2</Link>
      <DesignIcon name="library-ChevronRight" />
      <Link href={libraryHref()} aria-current={!parts.length && !current ? "page" : undefined}>All documents</Link>
      {parts.map((part, index) => (
        <span key={part.prefix} className={styles.crumbPart}>
          <DesignIcon name="library-ChevronRight" />
          <Link href={libraryHref(part.prefix)} aria-current={index === parts.length - 1 && !current ? "page" : undefined}>
            {part.label}
          </Link>
        </span>
      ))}
      {current && (
        <span className={styles.crumbPart}>
          <DesignIcon name="library-ChevronRight" />
          <span aria-current="page">{current}</span>
        </span>
      )}
    </nav>
  );
}

export function KnowledgeTopPath({
  prefix,
  fileLabel,
  current,
}: {
  prefix: string;
  fileLabel?: string;
  current?: string;
}) {
  const { root } = useKnowledge();
  const parts = breadcrumbParts(root, prefix);
  return (
    <nav className={styles.topPath} aria-label="Workspace path">
      <Link href={libraryHref()}>Document library</Link>
      <span>{"  /  "}</span>
      <Link href={libraryHref()}>Cloudflare R2</Link>
      {parts.map(part => (
        <span key={part.prefix}>
          <span>{"  /  "}</span>
          <Link href={libraryHref(part.prefix)}>{part.label}</Link>
        </span>
      ))}
      {fileLabel && (
        <>
          <span>{"  /  "}</span>
          <span>{fileLabel}</span>
        </>
      )}
      {current && (
        <>
          <span>{"  /  "}</span>
          <span className={styles.topPathCurrent}>{current}</span>
        </>
      )}
    </nav>
  );
}

export function FolderBrowser({
  prefix,
  onSelect,
  showDestinationNote = false,
  id,
}: {
  prefix: string;
  onSelect: (prefix: string) => void;
  showDestinationNote?: boolean;
  id?: string;
}) {
  const { root, folderPages, remember } = useKnowledge();
  const [expanded, setExpanded] = useState<string[]>([root]);
  const [error, setError] = useState("");
  const [loadingMore, setLoadingMore] = useState(false);
  const controllers = useRef(new Set<AbortController>());

  useEffect(() => () => {
    for (const controller of controllers.current) controller.abort();
  }, []);

  useEffect(() => {
    const ancestorPrefixes = breadcrumbParts(root, prefix).map(p => p.prefix);
    setExpanded(keys => Array.from(new Set([...keys, root, ...ancestorPrefixes])));
    for (const folder of [root, ...ancestorPrefixes]) {
      if (!folderPages[folder]) void load(folder);
    }
  }, [prefix, root]); // eslint-disable-line react-hooks/exhaustive-deps

  async function load(folder: string, more = false) {
    const existing = folderPages[folder];
    if (existing && !more) return;
    const controller = new AbortController();
    controllers.current.add(controller);
    try {
      setError("");
      const page = await readKnowledgePage(
        knowledgeApi,
        folder,
        more ? existing?.nextContinuationToken ?? undefined : undefined,
        controller.signal,
      );
      if (!controller.signal.aborted) remember(more && existing ? appendKnowledgePage(existing, page) : page);
    } catch (e) {
      if (!isAborted(e) && !controller.signal.aborted) setError(knowledgeError(e));
    } finally {
      controllers.current.delete(controller);
    }
  }

  function selectFolder(targetPrefix: string) {
    onSelect(targetPrefix);
    setExpanded(keys => keys.includes(targetPrefix) ? keys : [...keys, targetPrefix]);
    if (!folderPages[targetPrefix]) void load(targetPrefix);
  }

  function renderFolderNodes(parentPrefix: string, depth: number): React.ReactNode {
    const subFolders = (folderPages[parentPrefix]?.folders ?? []).filter(
      row => row.prefix.startsWith(parentPrefix) && row.prefix !== parentPrefix,
    );
    return subFolders.map(folder => {
      const isSelected = folder.prefix === prefix;
      const isOpen = expanded.includes(folder.prefix) || prefix.startsWith(folder.prefix);
      const loadedPage = folderPages[folder.prefix];
      const countLabel = loadedPage
        ? `${loadedPage.files.length}${loadedPage.nextContinuationToken ? "+" : ""}`
        : undefined;
      return (
        <div key={folder.prefix}>
          <button
            type="button"
            className={`${styles.folderRow} ${isSelected ? styles.folderRowActive : ""} ${depth > 0 ? styles.folderRowChild : ""}`}
            style={depth > 1 ? { paddingLeft: `${8 + depth * 20}px` } : undefined}
            aria-current={isSelected ? "page" : undefined}
            onClick={() => selectFolder(folder.prefix)}
          >
            <DesignIcon name={isSelected || isOpen ? "library-FolderOpen" : "library-Folder"} />
            <span className={styles.folderRowLabel}>{folder.name}</span>
            {countLabel !== undefined && <span className={styles.folderRowCount}>{countLabel}</span>}
          </button>
          {isOpen && loadedPage && renderFolderNodes(folder.prefix, depth + 1)}
        </div>
      );
    });
  }

  const rootPage = folderPages[root];
  const rootCount = rootPage ? `${rootPage.files.length}${rootPage.nextContinuationToken ? "+" : ""}` : "0";
  const selectedParts = breadcrumbParts(root, prefix);
  const selectedName = selectedParts.at(-1)?.label || "All documents";

  return (
    <aside id={id} className={styles.folderBrowser} aria-label="R2 folders">
      <div className={styles.storageHeading}>
        <DesignIcon name="library-Database" />
        <span>Cloudflare R2</span>
      </div>
      <p className={styles.bucket}>knowledge-heritage</p>

      <nav className={styles.folderList} aria-label="Folder tree">
        <button
          type="button"
          className={`${styles.folderRow} ${prefix === root ? styles.folderRowActive : ""}`}
          aria-current={prefix === root ? "page" : undefined}
          onClick={() => selectFolder(root)}
        >
          <DesignIcon name={prefix === root ? "library-FolderOpen" : "library-Folder"} />
          <span className={styles.folderRowLabel}>All documents</span>
          <span className={styles.folderRowCount}>{rootCount}</span>
        </button>
        {renderFolderNodes(root, 0)}
      </nav>

      {folderPages[prefix]?.nextContinuationToken && (
        <button
          type="button"
          className={styles.figmaBtn}
          disabled={loadingMore}
          onClick={async () => {
            setLoadingMore(true);
            await load(prefix, true);
            setLoadingMore(false);
          }}
        >
          {loadingMore ? "Loading…" : "Load more folders"}
        </button>
      )}

      {error && (
        <div role="alert" className={styles.error}>
          <p>{error}</p>
          <button type="button" className={styles.figmaBtn} onClick={() => void load(prefix)}>
            Retry folders
          </button>
        </div>
      )}

      {showDestinationNote && (
        <p className={styles.treeNote}>
          Selected destination: {selectedName}. Folder counts include loaded completed uploads only.
        </p>
      )}
      <p className={styles.treeNote}>
        Folders organize stored files. They do not change review or indexing status.
      </p>
    </aside>
  );
}
