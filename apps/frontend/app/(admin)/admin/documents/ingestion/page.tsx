"use client";

import Link from "next/link";
import { Button } from "antd";
import { DesignIcon } from "@/features/knowledge/DesignIcon";
import { libraryHref } from "@/features/knowledge/folder-state";
import styles from "@/features/knowledge/knowledge.module.css";

export default function IngestionPage() {
  return (
    <section className={styles.page} aria-label="RAG Ingestion">
      <header className={styles.header}>
        <div>
          <h1>Ingestion</h1>
          <p>Monitor chunking, embedding (BGE-M3), and indexing jobs for approved knowledge documents.</p>
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
            Objects stored in <code>knowledge-heritage</code> are verified in Cloudflare R2 only. Storage completion never triggers automatic indexing.
          </p>
        </div>
        <div className={styles.panel}>
          <div className={styles.stateTitle}>
            <strong>Ingestion job API</strong>
            <span className={styles.badges}>Unavailable</span>
          </div>
          <p className={styles.muted}>
            The mounted <code>/api/admin/knowledge</code> contract does not expose ingestion job creation, progress stages, chunk inspection, or retry endpoints.
          </p>
        </div>
        <div className={styles.panel}>
          <div className={styles.stateTitle}>
            <strong>Chatbot availability</strong>
            <span className={styles.badges}>Separate from R2 upload</span>
          </div>
          <p className={styles.muted}>
            Uploaded R2 files are never marked as indexed or chatbot-ready without a verified backend ingestion pipeline response.
          </p>
        </div>
      </div>

      <div className={styles.panel}>
        <div className={styles.empty}>
          <DesignIcon name="library-Hash" />
          <h2>RAG ingestion job endpoints are not exposed for R2 library objects</h2>
          <p className={styles.muted}>
            No simulated indexing jobs or percentage bars are shown. Manage and verify your stored source files in the R2 Document library.
          </p>
          <div className={styles.actions}>
            <Link href={libraryHref()}>
              <Button type="primary">Open Document library</Button>
            </Link>
            <Button disabled>Start ingestion job (unavailable)</Button>
            <Button disabled>Retry failed job (unavailable)</Button>
          </div>
        </div>
      </div>
    </section>
  );
}
