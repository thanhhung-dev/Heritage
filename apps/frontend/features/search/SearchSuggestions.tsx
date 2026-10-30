import { HeritageResultCard } from "@/features/search/HeritageResultCard";
import type { HeritageSearchItem } from "@/features/search/types";
import styles from "@/features/search/search.module.css";

export function SearchSuggestions({ items, loading, error }: { items: HeritageSearchItem[]; loading: boolean; error: boolean }) {
  return <section className={styles.recommendations} aria-labelledby="search-recommendations-title">
    <h2 id="search-recommendations-title">Recommend For You</h2>
    {loading ? <div className={styles.recommendationGrid} aria-hidden="true">{Array.from({ length: 5 }, (_, index) => <div key={index} className={`${styles.recommendationSkeleton} ${styles.skeleton}`} />)}</div>
      : items.length ? <div className={styles.recommendationGrid}>{items.map((item) => <HeritageResultCard key={item.slug} item={item} recommendation />)}</div>
        : <p className={styles.recommendationNote}>{error ? "Recommendations will return when the catalogue is available." : "More tours are on the way. Check back soon."}</p>}
  </section>;
}
