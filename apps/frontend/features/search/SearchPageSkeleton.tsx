import { SearchHero } from "@/features/search/SearchHero";
import { SearchResultsSkeleton } from "@/features/search/SearchResultsList";
import { SearchSuggestions } from "@/features/search/SearchSuggestions";
import styles from "@/features/search/search.module.css";

export function SearchPageSkeleton() {
  return <div className={styles.page} data-search-page>
    <SearchHero />
    <div className={styles.content}>
      <div className={`${styles.querySkeleton} ${styles.skeleton}`} aria-hidden="true" />
      <div className={styles.resultsHeading}><h2>Search Results</h2></div>
      <div className={styles.contentGrid}>
        <div className={styles.filterSkeleton} aria-hidden="true"><i /><i /><i /><i /><i /></div>
        <SearchResultsSkeleton />
      </div>
      <SearchSuggestions items={[]} loading error={false} />
    </div>
  </div>;
}
