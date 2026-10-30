import { HeritageResultCard } from "@/features/search/HeritageResultCard";
import { SEARCH_PAGE_SIZE } from "@/features/search/search-params";
import type { HeritageSearchItem } from "@/features/search/types";
import styles from "@/features/search/search.module.css";

export function SearchResultsList({ items }: { items: HeritageSearchItem[] }) {
  return <div className={styles.resultList}>{items.map((item) => <HeritageResultCard key={item.slug} item={item} />)}</div>;
}

export function SearchResultsSkeleton() {
  return <div className={styles.resultList} role="status" aria-label="Loading tours">
    <span className={styles.srOnly}>Loading search results…</span>
    {Array.from({ length: SEARCH_PAGE_SIZE }, (_, index) => <div className={styles.skeletonRow} key={index} aria-hidden="true">
      <div className={`${styles.skeletonThumbnail} ${styles.skeleton}`} /><div className={styles.skeletonBody}><i /><i /><i /><i /></div>
    </div>)}
  </div>;
}
