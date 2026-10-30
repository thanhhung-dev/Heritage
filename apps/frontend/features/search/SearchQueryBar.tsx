"use client";

import { CloseOutlined, SearchOutlined } from "@ant-design/icons";
import { useRef } from "react";
import styles from "@/features/search/search.module.css";

interface SearchQueryBarProps {
  query: string;
  filtered: boolean;
  onChange: (value: string) => void;
  onComposing: (value: boolean) => void;
  onSubmit: () => void;
  onReset: () => void;
}

export function SearchQueryBar({ query, filtered, onChange, onComposing, onSubmit, onReset }: SearchQueryBarProps) {
  const input = useRef<HTMLInputElement>(null);
  return <div className={styles.queryBar}>
    <form role="search" aria-label="Search virtual tours" className={styles.searchForm} onSubmit={(event) => { event.preventDefault(); onSubmit(); }}>
      <button type="submit" className={styles.searchIcon} aria-label="Search tours"><SearchOutlined /></button>
      <label className={styles.srOnly} htmlFor="heritage-query">Search tours</label>
      <input ref={input} id="heritage-query" data-search-query type="search" name="q" value={query} maxLength={200}
        autoComplete="off" placeholder="Search tours…" onChange={(event) => onChange(event.target.value)}
        onCompositionStart={() => onComposing(true)} onCompositionEnd={(event) => { onChange(event.currentTarget.value); onComposing(false); }} />
      {query && <button className={styles.clearQuery} type="button" aria-label="Clear search query"
        onClick={() => { onChange(""); input.current?.focus(); }}><CloseOutlined /></button>}
    </form>
    <button className={styles.clearAll} type="button" disabled={!filtered} onClick={onReset}>Clear all</button>
  </div>;
}
