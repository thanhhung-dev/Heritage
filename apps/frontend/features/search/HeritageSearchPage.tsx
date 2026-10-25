"use client";

import { useEffect, useState } from "react";
import { useSearchUrl } from "./useSearchUrl";
import { useHeritageSearch } from "./useHeritageSearch";
import { SearchToolbar } from "./SearchToolbar";
import { SearchResultsGrid, SearchResultsSkeleton } from "./SearchResultsGrid";
import { SearchPagination } from "./SearchPagination";
import { SearchFeedback } from "./SearchFeedback";
import styles from "./search.module.css";

export function HeritageSearchPage() {
  const url = useSearchUrl();
  const { navigate } = url;
  const requestedPage = url.state.page;
  const { snapshot, retry } = useHeritageSearch(url.state);
  const [facets, setFacets] = useState<{ regions: string[]; categories: string[] }>({
    regions: [],
    categories: [],
  });
  const results = snapshot.status === "success" ? snapshot.results : null;
  const loading = url.busy || snapshot.status === "loading";

  useEffect(() => {
    if (!results) return;
    setFacets({ regions: results.regions, categories: results.categories });
    if (results.page !== requestedPage) navigate({ page: results.page }, true);
  }, [results, requestedPage, navigate]);

  const filtered = Boolean(url.state.q || url.state.region || url.state.category);
  const first = results && results.total > 0 ? (results.page - 1) * results.pageSize + 1 : 0;
  const last = results ? Math.min(results.page * results.pageSize, results.total) : 0;

  return (
    <div className={styles.page}>
      <header className={styles.intro}>
        <p className={styles.eyebrow}>ĐÀ NẴNG · HUẾ</p>
        <h1>
          Tìm một di sản.<br />
          <span>Mở một câu chuyện.</span>
        </h1>
        <p>
          Đi qua những miền đất, chạm vào những giá trị còn mãi.
          Bạn muốn khám phá điều gì hôm nay?
        </p>
      </header>
      <SearchToolbar
        query={url.draft}
        state={url.state}
        regions={facets.regions}
        categories={facets.categories}
        onQueryChange={url.setDraft}
        onComposingChange={url.setComposing}
        onSubmit={url.submit}
        onFilter={url.filter}
        onReset={url.reset}
      />
      <section className={styles.results} aria-labelledby="search-results-title" aria-busy={loading}>
        <div className={styles.resultsHeading}>
          <h2 id="search-results-title">
            {url.state.q ? `Kết quả cho “${url.state.q}”` : "Khám phá di sản"}
          </h2>
          <p role="status" aria-live="polite" aria-atomic="true">
            {loading ? "Đang tìm kiếm…" : results
              ? `${results.total} di sản${results.total ? ` · Hiển thị ${first}–${last}` : ""}`
              : "Tạm thời chưa có kết quả"}
          </p>
        </div>
        {loading ? (
          <SearchResultsSkeleton />
        ) : snapshot.status === "error" ? (
          <SearchFeedback error filtered={filtered} onRetry={retry} onReset={url.reset} />
        ) : results && results.items.length > 0 ? (
          <>
            <SearchResultsGrid items={results.items} />
            <SearchPagination
              page={results.page}
              pageCount={results.pageCount}
              hrefForPage={url.hrefForPage}
            />
          </>
        ) : (
          <SearchFeedback filtered={filtered} onRetry={retry} onReset={url.reset} />
        )}
      </section>
    </div>
  );
}
