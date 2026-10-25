"use client";

import { CloseOutlined, SearchOutlined } from "@ant-design/icons";
import { useRef } from "react";
import type { SearchState } from "./types";
import styles from "./search.module.css";

interface SearchToolbarProps {
  query: string;
  state: SearchState;
  regions: string[];
  categories: string[];
  onQueryChange: (value: string) => void;
  onComposingChange: (value: boolean) => void;
  onSubmit: () => void;
  onFilter: (patch: Pick<Partial<SearchState>, "region" | "category">) => void;
  onReset: () => void;
}

export function SearchToolbar({
  query, state, regions, categories, onQueryChange,
  onComposingChange, onSubmit, onFilter, onReset,
}: SearchToolbarProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const hasFilters = Boolean(query || state.region || state.category);
  const regionOptions = [...new Set([...regions, ...(state.region ? [state.region] : [])])];
  const categoryOptions = [...new Set([...categories, ...(state.category ? [state.category] : [])])];
  return (
    <div className={styles.toolbar}>
      <form
        className={styles.searchForm}
        role="search"
        aria-label="Tìm kiếm di sản"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <label className={styles.srOnly} htmlFor="heritage-query">Tên di sản hoặc từ khóa</label>
        <SearchOutlined className={styles.searchIcon} aria-hidden />
        <input
          ref={inputRef}
          id="heritage-query"
          name="q"
          type="search"
          value={query}
          autoComplete="off"
          placeholder="Tìm tên di sản, địa điểm, câu chuyện…"
          onChange={(event) => onQueryChange(event.target.value)}
          onCompositionStart={() => onComposingChange(true)}
          onCompositionEnd={(event) => {
            onQueryChange(event.currentTarget.value);
            onComposingChange(false);
          }}
        />
        {query && (
          <button
            className={styles.clearQuery}
            type="button"
            aria-label="Xóa từ khóa"
            onClick={() => {
              onQueryChange("");
              inputRef.current?.focus();
            }}
          >
            <CloseOutlined aria-hidden />
          </button>
        )}
        <button className={styles.primaryButton} type="submit">Tìm kiếm</button>
      </form>
      <div className={styles.filters}>
        <label className={styles.filter}>
          <span>Vùng miền</span>
          <select name="region" value={state.region} onChange={(event) => onFilter({ region: event.target.value })}>
            <option value="">Tất cả vùng miền</option>
            {regionOptions.map((region) => <option key={region} value={region}>{region}</option>)}
          </select>
        </label>
        <label className={styles.filter}>
          <span>Danh mục</span>
          <select name="category" value={state.category} onChange={(event) => onFilter({ category: event.target.value })}>
            <option value="">Tất cả danh mục</option>
            {categoryOptions.map((category) => <option key={category} value={category}>{category}</option>)}
          </select>
        </label>
        {hasFilters && (
          <button className={styles.resetButton} type="button" onClick={onReset}>
            <CloseOutlined aria-hidden /> Xóa tìm kiếm và bộ lọc
          </button>
        )}
      </div>
    </div>
  );
}
