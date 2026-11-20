"use client";

import Link from "next/link";
import { Button, Spin } from "antd";
import { ApiError } from "../../lib/api";
import { knowledgeError } from "../../services/knowledge.service";
import styles from "./knowledge.module.css";

export function KnowledgeFeedback({ error, retry, loading = false }: { error?: unknown; retry?: () => void; loading?: boolean }) {
  if (loading) return <div className={styles.empty} role="status"><Spin /><p>Loading knowledge library…</p></div>;
  const status = error instanceof ApiError ? error.status : undefined;
  return <div className={styles.error} role="alert">
    <h2>{status === 401 ? "Sign in to continue" : status === 403 ? "Administrator access required" : "Unable to load this content"}</h2>
    <p>{knowledgeError(error)}</p>
    <div className={styles.actions}>
      {status === 401 && <Link href="/sign-in?next=%2Fadmin%2Fdocuments"><Button type="primary">Sign in</Button></Link>}
      {retry && <Button onClick={retry}>Try again</Button>}
      {status === 403 && <Link href="/">Back to Heritage</Link>}
    </div>
  </div>;
}
