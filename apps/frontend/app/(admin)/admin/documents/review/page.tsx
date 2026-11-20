"use client";

import Link from "next/link";
import { DesignIcon } from "@/features/knowledge/DesignIcon";
import { KnowledgeTopPath } from "@/features/knowledge/FolderBrowser";
import { libraryHref } from "@/features/knowledge/folder-state";
import { useKnowledge } from "@/features/knowledge/KnowledgeProvider";
import styles from "@/features/knowledge/knowledge.module.css";

export default function PendingReviewPage() {
  const { root } = useKnowledge();
  return (
    <section className={styles.page} aria-label="Pending review">
      <KnowledgeTopPath prefix={root} current="Pending review" />

      <header className={styles.header}>
        <div>
          <h1>Pending review</h1>
          <p>Review submitted document revisions before approving them for RAG ingestion.</p>
        </div>
        <div className={styles.actions}>
          <Link href={libraryHref()} className={styles.figmaBtn}>
            Back to library
          </Link>
        </div>
      </header>

      <div className={styles.contextBar}>
        <span className={styles.contextBadge}>REVIEW UNAVAILABLE</span>
        <span className={styles.contextText}>
          Review tools are not enabled for this library yet.
        </span>
      </div>

      <div className={styles.stateCards}>
        <div className={styles.stateCard}>
          <div className={styles.stateTitle}>
            <span className={styles.stateLabel}>Storage</span>
            <span className={styles.badges}>Active in R2</span>
          </div>
          <p className={styles.stateSummary}>Original files are stored and verified in bucket knowledge-heritage.</p>
        </div>
        <div className={styles.stateCard}>
          <div className={styles.stateTitle}>
            <span className={styles.stateLabel}>Review queue API</span>
            <span className={styles.badges}>Unavailable</span>
          </div>
          <p className={styles.stateSummary}>No pending review list or approve/request-changes endpoints are mounted.</p>
        </div>
        <div className={styles.stateCard}>
          <div className={styles.stateTitle}>
            <span className={styles.stateLabel}>Ingestion</span>
            <span className={styles.badges}>Separate step</span>
          </div>
          <p className={styles.stateSummary}>Approval never automatically indexes a document into the chatbot.</p>
        </div>
      </div>

      <div className={styles.twoColumns}>
        <div className={styles.mainColumn} style={{ gap: 20 }}>
          <div className={styles.panel}>
            <div className={styles.panelHeading}>
              <h2>Submissions awaiting review</h2>
              <p>The review queue is not available yet.</p>
            </div>

            <div className={styles.figmaTable} role="table" aria-label="Pending review submissions">
              <div className={styles.figmaTableHeader} role="row">
                <div className={styles.colFile} role="columnheader">Document / revision</div>
                <div className={styles.colUpdated} role="columnheader">Submitted</div>
                <div className={styles.colReview} role="columnheader">Review</div>
                <div className={styles.colActions} role="columnheader">Actions</div>
              </div>
              <div className={styles.empty}>
                <DesignIcon name="library-ClipboardCheck" />
                <h2>Review workflow API is not available</h2>
                <p className={styles.muted}>
                  Uploaded documents in <code>knowledge-heritage</code> are stored in Cloudflare R2. Because the backend does not expose revision submission or review queue endpoints, no fabricated review items are shown.
                </p>
                <Link href={libraryHref()} className={`${styles.figmaBtn} ${styles.figmaBtnPrimary}`}>
                  Open Document library
                </Link>
              </div>
            </div>
          </div>
        </div>

        <div className={styles.mainColumn} style={{ gap: 16 }}>
          <div className={styles.panel}>
            <div className={styles.panelHeading}>
              <h2>Review decision</h2>
              <p>Approve a revision for ingestion or request metadata changes.</p>
            </div>
            <div className={styles.fieldRow}>
              <label htmlFor="review-decision-note">Reviewer note</label>
              <div className={styles.readonlyControl} id="review-decision-note">
                <span className={styles.muted}>Decision API unavailable in current backend</span>
              </div>
            </div>
            <div className={styles.actions}>
              <button type="button" className={styles.figmaBtn} disabled>
                Request changes
              </button>
              <button type="button" className={`${styles.figmaBtn} ${styles.figmaBtnPrimary}`} disabled>
                Approve revision
              </button>
            </div>
          </div>

          <div className={styles.notice}>
            <DesignIcon name="library-Info" />
            <div className={styles.noticeBody}>
              <span className={styles.noticeTitle}>Approval ≠ ingestion</span>
              <p>
                Review decisions are never simulated in local Frontend state. Once backend review endpoints are mounted, approved revisions can be queued for RAG ingestion separately.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
