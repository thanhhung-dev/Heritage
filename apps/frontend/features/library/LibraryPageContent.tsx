"use client";

import { useEffect, useState } from "react";
import { PortraitCard } from "@/components/PortraitCard/PortraitCard";
import { fetchHeritages } from "@/lib/heritage";
import type { HeritageSummary } from "@/types/heritage";
import styles from "./library.module.css";

export function LibraryPageContent() {
  const [items, setItems] = useState<HeritageSummary[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  useEffect(() => {
    let active = true;
    fetchHeritages().then((data) => {
      if (active) { setItems(data); setStatus("ready"); }
    }).catch(() => { if (active) setStatus("error"); });
    return () => { active = false; };
  }, []);

  return (
    <div className={styles.library}>
      <section className={styles.hero}>
        <h1>HERITAGE Virtual Tours</h1>
        <p>Discover our library of immersive experiences</p>
      </section>
      <section className={styles.content} aria-label="Heritage library">
        {status === "loading" && <p role="status">Loading heritage experiences…</p>}
        {status === "error" && <p role="alert">Unable to load heritage experiences.</p>}
        {status === "ready" && items.length === 0 && <p>No heritage experiences available.</p>}
        <div className={styles.grid}>
          {items.map((item) => <PortraitCard key={item.slug} variant="library" item={{ ...item, href: `/content/${encodeURIComponent(item.slug)}` }} />)}
        </div>
      </section>
    </div>
  );
}
