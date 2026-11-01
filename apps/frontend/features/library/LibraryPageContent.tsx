"use client";

import { useEffect, useState } from "react";
import { PortraitCard } from "@/components/PortraitCard/PortraitCard";
import { Pagination } from "@/components/Pagination/Pagination";
import { fetchHeritages } from "@/lib/heritage";
import type { HeritageSummary } from "@/types/heritage";
import styles from "./library.module.css";

export function LibraryPageContent() {
  const [items, setItems] = useState<HeritageSummary[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [query, setQuery] = useState("");
  const [region, setRegion] = useState("");
  const [language, setLanguage] = useState("");
  const [order, setOrder] = useState("newest");
  const [page, setPage] = useState(1);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const restore = () => {
      const params = new URLSearchParams(window.location.search);
      setQuery(params.get("q") ?? "");
      setRegion(params.get("region") ?? "");
      setLanguage(params.get("language") ?? "");
      setOrder(params.get("order") === "oldest" ? "oldest" : "newest");
      const number = Number(params.get("page"));
      setPage(Number.isSafeInteger(number) && number > 0 ? number : 1);
    };
    restore();
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);

  function updateUrl(key: string, value: string, replace = false) {
    const url = new URL(window.location.href);
    if (value) url.searchParams.set(key, value);
    else url.searchParams.delete(key);
    if (key !== "page") url.searchParams.delete("page");
    window.history[replace ? "replaceState" : "pushState"](null, "", url);
  }

  const regions = Array.from(new Set(items.map((item) => item.region).filter((value): value is string => Boolean(value)))).sort();
  const languages = Array.from(new Set(items.flatMap((item) => [item.language1?.name, item.language2?.name]).filter((value): value is string => Boolean(value)))).sort();
  const filtered = items.filter((item) => {
    const text = `${item.title} ${item.region ?? ""}`.toLocaleLowerCase();
    return text.includes(query.trim().toLocaleLowerCase()) && (!region || item.region === region) && (!language || [item.language1?.name, item.language2?.name].includes(language));
  }).sort((a, b) => {
    const left = a.publish_date;
    const right = b.publish_date;
    if (!left) return right ? 1 : 0;
    if (!right) return -1;
    return order === "newest" ? right.localeCompare(left) : left.localeCompare(right);
  });
  const totalPages = Math.ceil(filtered.length / 20);
  const currentPage = Math.min(page, Math.max(totalPages, 1));
  const visibleItems = filtered.slice((currentPage - 1) * 20, currentPage * 20);

  useEffect(() => {
    let active = true;
    setStatus("loading");
    fetchHeritages().then((data) => {
      if (!Array.isArray(data)) throw new Error("Invalid heritage list");
      if (active) { setItems(data); setStatus("ready"); }
    }).catch(() => { if (active) setStatus("error"); });
    return () => { active = false; };
  }, [attempt]);

  return (
    <div className={styles.library}>
      <section className={styles.hero}>
        <h1>HERITAGE Virtual Tours</h1>
        <p>Discover our library of immersive experiences</p>
      </section>
      <section className={styles.content} aria-label="Heritage library">
        <div className={styles.filters} role="search" aria-label="Filter heritage experiences">
          <label className={styles.search}><span className={styles.srOnly}>Search tours</span><input type="search" placeholder="Search tours…" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); updateUrl("q", event.target.value, true); }} /></label>
          <label><span className={styles.srOnly}>Publish date</span><select value={order} onChange={(event) => { setOrder(event.target.value); setPage(1); updateUrl("order", event.target.value === "newest" ? "" : event.target.value); }}><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select></label>
          <label><span className={styles.srOnly}>Region</span><select value={region} onChange={(event) => { setRegion(event.target.value); setPage(1); updateUrl("region", event.target.value); }}><option value="">All regions</option>{region && !regions.includes(region) && <option value={region}>{region} (unavailable)</option>}{regions.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label><span className={styles.srOnly}>Language</span><select value={language} onChange={(event) => { setLanguage(event.target.value); setPage(1); updateUrl("language", event.target.value); }}><option value="">All languages</option>{language && !languages.includes(language) && <option value={language}>{language} (unavailable)</option>}{languages.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <button type="button" onClick={() => { setQuery(""); setRegion(""); setLanguage(""); setOrder("newest"); setPage(1); const url = new URL(window.location.href); ["q", "region", "language", "order", "page"].forEach((key) => url.searchParams.delete(key)); window.history.pushState(null, "", url); }}>Clear all</button>
        </div>
        {status === "loading" && <p role="status">Loading heritage experiences…</p>}
        {status === "error" && <div className={styles.state} role="alert"><p>Unable to load heritage experiences.</p><button type="button" onClick={() => setAttempt((value) => value + 1)}>Try again</button></div>}
        {status === "ready" && items.length === 0 && <p>No heritage experiences available.</p>}
        {status === "ready" && items.length > 0 && filtered.length === 0 && <p role="status" className={styles.state}>No tours found matching your filters.</p>}
        {status === "ready" && <div className={styles.grid}>
          {visibleItems.map((item) => <PortraitCard key={item.slug} variant="library" item={{ ...item, href: `/content/${encodeURIComponent(item.slug)}` }} />)}
        </div>}
        {status === "ready" && <Pagination page={currentPage} totalPages={totalPages} onPageChange={(value) => { setPage(value); updateUrl("page", value === 1 ? "" : String(value)); }} />}
      </section>
    </div>
  );
}
