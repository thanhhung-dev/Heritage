import { HeritageResultCard } from "./HeritageResultCard";
import type { HeritageSearchItem } from "./types";
import { SEARCH_PAGE_SIZE } from "./search-params";
import styles from "./search.module.css";

export function SearchResultsGrid({ items }: { items: HeritageSearchItem[] }) {
  return (
    <div className={styles.grid}>
      {items.map((item) => <HeritageResultCard key={item.slug} item={item} />)}
    </div>
  );
}

export function SearchResultsSkeleton() {
  return (
    <div role="status" aria-label="Đang tìm kiếm di sản">
      <span className={styles.srOnly}>Đang tải kết quả…</span>
      <div className={styles.grid} aria-hidden="true">
        {Array.from({ length: SEARCH_PAGE_SIZE }, (_, index) => (
          <div className={styles.skeletonCard} key={index}>
            <div className={`${styles.skeletonImage} ${styles.skeleton}`} />
            <div className={styles.cardBody}>
              <div className={styles.skeleton} />
              <div className={styles.skeleton} />
              <div className={styles.skeleton} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
