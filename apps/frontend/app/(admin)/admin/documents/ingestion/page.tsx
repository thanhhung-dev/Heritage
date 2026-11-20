"use client";

import Link from "next/link";
import { DesignIcon } from "@/features/knowledge/DesignIcon";
import { KnowledgeTopPath } from "@/features/knowledge/FolderBrowser";
import { libraryHref } from "@/features/knowledge/folder-state";
import { useKnowledge } from "@/features/knowledge/KnowledgeProvider";
import styles from "@/features/knowledge/knowledge.module.css";

export default function IngestionPage() {
  const { root } = useKnowledge();
  return (
    <section className={styles.page} aria-label="RAG Ingestion">
      <KnowledgeTopPath prefix={root} current="Ingestion" />

      <header className={styles.header}>
        <div>
          <h1>Ingestion</h1>
          <p>Run and monitor extraction, chunking, BGE-M3 embedding, and indexing jobs for approved revisions.</p>
        </div>
        <div className={styles.actions}>
          <button type="button" className={`${styles.figmaBtn} ${styles.figmaBtnPrimary}`} disabled>
            Run ingestion
          </button>
          <Link href={libraryHref()} className={styles.figmaBtn}>
            Back to library
          </Link>
        </div>
      </header>

      <div className={styles.contextBar}>
        <span className={styles.contextBadge}>INGESTION UNAVAILABLE</span>
        <span className={styles.contextText}>
          Ingestion tools are not enabled for this library yet.
        </span>
      </div>

      <div className={styles.stateCards}>
        <div className={styles.stateCard}>
          <div className={styles.stateTitle}>
            <span className={styles.stateLabel}>Storage</span>
            <span className={styles.badges}>Stored in R2</span>
          </div>
          <p className={styles.stateSummary}>Source files are stored in bucket knowledge-heritage.</p>
        </div>
        <div className={styles.stateCard}>
          <div className={styles.stateTitle}>
            <span className={styles.stateLabel}>Ingestion jobs</span>
            <span className={styles.badges}>Unavailable</span>
          </div>
          <p className={styles.stateSummary}>Job creation, stage progress, and retry endpoints are not mounted.</p>
        </div>
        <div className={styles.stateCard}>
          <div className={styles.stateTitle}>
            <span className={styles.stateLabel}>Chatbot availability</span>
            <span className={styles.badges}>Unavailable</span>
          </div>
          <p className={styles.stateSummary}>Files are never marked as chatbot-ready without a real indexing response.</p>
        </div>
      </div>

      <div className={styles.twoColumns}>
        <div className={styles.mainColumn} style={{ gap: 20 }}>
          <div className={styles.panel}>
            <div className={styles.panelHeading}>
              <h2>Ingestion jobs</h2>
              <p>Job information is not available yet.</p>
            </div>

            <div className={styles.figmaTable} role="table" aria-label="Ingestion jobs">
              <div className={styles.figmaTableHeader} role="row">
                <div className={styles.colFile} role="columnheader">Job / document</div>
                <div className={styles.colReview} role="columnheader">Stage</div>
                <div className={styles.colIngestion} role="columnheader">Status</div>
                <div className={styles.colActions} role="columnheader">Actions</div>
              </div>
              <div className={styles.empty}>
                <DesignIcon name="library-Hash" />
                <h2>No ingestion job API is connected</h2>
                <p className={styles.muted}>
                  The backend Knowledge Library currently implements the 8 Cloudflare R2 storage endpoints. Extraction, chunking, BGE-M3 embedding, and vector indexing job APIs are not exposed for these objects.
                </p>
                <Link href={libraryHref()} className={`${styles.figmaBtn} ${styles.figmaBtnPrimary}`}>
                  Browse R2 Document library
                </Link>
              </div>
            </div>
          </div>
        </div>

        <div className={styles.mainColumn} style={{ gap: 16 }}>
          <div className={styles.panel}>
            <div className={styles.panelHeading}>
              <h2>Pipeline stages</h2>
              <p>Expected stages once backend ingestion job endpoints are connected.</p>
            </div>
            <div className={styles.metaStack}>
              <div className={styles.metaField}>
                <span className={styles.metaFieldLabel}>1. Text extraction & validation</span>
                <span className={styles.metaFieldValue}>Unavailable · Text preview is available in Document details</span>
              </div>
              <div className={styles.metaField}>
                <span className={styles.metaFieldLabel}>2. Semantic chunking</span>
                <span className={styles.metaFieldValue}>Unavailable</span>
              </div>
              <div className={styles.metaField}>
                <span className={styles.metaFieldLabel}>3. BGE-M3 embedding generation</span>
                <span className={styles.metaFieldValue}>Unavailable</span>
              </div>
              <div className={styles.metaField}>
                <span className={styles.metaFieldLabel}>4. Search index publication</span>
                <span className={styles.metaFieldValue}>Unavailable</span>
              </div>
            </div>
            <div>
              <button type="button" className={styles.figmaBtn} disabled>
                Retry failed job (unavailable)
              </button>
            </div>
          </div>

          <div className={styles.notice}>
            <DesignIcon name="library-Info" />
            <div className={styles.noticeBody}>
              <span className={styles.noticeTitle}>Storage state ≠ Ingestion state</span>
              <p>
                Uploading a file to <code>knowledge-heritage</code> only completes R2 storage. It never simulates or triggers background RAG indexing.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
