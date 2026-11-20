"use client";

import Link from "next/link";
import { Button } from "antd";
import { DesignIcon } from "@/features/knowledge/DesignIcon";
import { libraryHref } from "@/features/knowledge/folder-state";
import styles from "@/features/knowledge/knowledge.module.css";

export default function PendingReviewPage() {
  return (
    <section className={styles.page} aria-label="Pending review">
      <header className={styles.header}>
        <div>
          <h1>Pending review</h1>
          <p>Review submitted document revisions before approving them for RAG ingestion.</p>
        </div>
        <div className={styles.actions}>
          <Link href={libraryHref()}>
            <Button icon={<DesignIcon name="library-ArrowLeft" />}>Back to Document library</Button>
          </Link>
        </div>
      </header>

      <div className={styles.stateCards}>
        <div className={styles.panel}>
          <div className={styles.stateTitle}>
            <strong>Storage state</strong>
            <span className={styles.badges}>Active in R2</span>
          </div>
          <p className={styles.muted}>
            Files uploaded to <code>knowledge-heritage</code> are physically stored in Cloudflare R2 and can be browsed, previewed, and downloaded in the Document library.
          </p>
        </div>
        <div className={styles.panel}>
          <div className={styles.stateTitle}>
            <strong>Review workflow API</strong>
            <span className={styles.badges}>Unavailable</span>
          </div>
          <p className={styles.muted}>
            The mounted backend does not expose document review state transitions (submit, approve, request changes) for R2 library objects.
          </p>
        </div>
        <div className={styles.panel}>
          <div className={styles.stateTitle}>
            <strong>Approve / Request changes</strong>
            <span className={styles.badges}>Disabled</span>
          </div>
          <p className={styles.muted}>
            Approval is never simulated in local Frontend state. Actions stay disabled until backend review endpoints are implemented.
          </p>
        </div>
      </div>

      <div className={styles.panel}>
        <div className={styles.empty}>
          <DesignIcon name="library-ClipboardCheck" />
          <h2>Document review queue API is not connected</h2>
          <p className={styles.muted}>
            Uploaded files in <code>knowledge-heritage</code> remain in pure R2 storage state. Use the Document library to inspect stored objects and preview raw UTF-8 text.
          </p>
          <div className={styles.actions}>
            <Link href={libraryHref()}>
              <Button type="primary">Open Document library</Button>
            </Link>
            <Button disabled>Approve revision (unavailable)</Button>
            <Button disabled>Request changes (unavailable)</Button>
          </div>
        </div>
      </div>
    </section>
  );
}
