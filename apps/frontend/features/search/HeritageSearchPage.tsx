"use client";

import { useEffect } from "react";
import { useSearchUrl } from "@/features/search/useSearchUrl";
import { useHeritageSearch } from "@/features/search/useHeritageSearch";
import { SearchHero } from "@/features/search/SearchHero";
import { SearchQueryBar } from "@/features/search/SearchQueryBar";
import { SearchFilters } from "@/features/search/SearchFilters";
import { SearchResultsList, SearchResultsSkeleton } from "@/features/search/SearchResultsList";
import { SearchPagination } from "@/features/search/SearchPagination";
import { SearchFeedback } from "@/features/search/SearchFeedback";
import { SearchSuggestions } from "@/features/search/SearchSuggestions";
import styles from "@/features/search/search.module.css";

export function HeritageSearchPage() {
  const url = useSearchUrl();
  const { navigate } = url;
  const { status, results, retry } = useHeritageSearch(url.state);
  const loading = status === "loading";
  useEffect(() => {
    if (results && results.page !== url.state.page) navigate({ page: results.page }, true);
  }, [results, url.state.page, navigate]);
  const filtered = Boolean(url.busy || url.draft || url.state.q || url.state.regions.length || url.state.categories.length || url.state.locations.length || url.state.page > 1);
  return <div className={styles.page} data-search-page>
    <SearchHero image={results?.heroImage} />
    <div className={styles.content}>
      <SearchQueryBar query={url.draft} filtered={filtered} onChange={url.setDraft} onComposing={url.setComposing} onSubmit={url.submit} onReset={url.reset} />
      <div className={styles.resultsHeading}>
        <h2 id="search-results-title">Search Results</h2>
        <p role="status" aria-live="polite" aria-atomic="true">{loading || url.busy ? "Searching…" : results ? `${results.total} ${results.total === 1 ? "tour" : "tours"}` : "Catalogue unavailable"}</p>
      </div>
      <div className={styles.contentGrid}>
        <SearchFilters state={url.state} categories={results?.categoryFacets ?? []} groups={results?.locationGroups ?? []} loading={loading} onToggle={url.toggle} />
        <section className={styles.results} aria-labelledby="search-results-title" aria-busy={loading || url.busy}>
          {loading ? <SearchResultsSkeleton /> : status === "error" ? <SearchFeedback error onRetry={retry} />
            : results?.items.length ? <><SearchResultsList items={results.items} /><SearchPagination page={results.page} pageCount={results.pageCount} hrefForPage={url.hrefForPage} pending={url.busy} /></>
              : <SearchFeedback onRetry={retry} />}
        </section>
      </div>
      <SearchSuggestions items={results?.recommendations ?? []} loading={loading} error={status === "error"} />
    </div>
  </div>;
}
