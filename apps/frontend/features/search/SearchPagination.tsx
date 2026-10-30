import Link from "next/link";
import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { paginationPages } from "./search-params";
import styles from "./search.module.css";

interface SearchPaginationProps {
  page: number;
  pageCount: number;
  hrefForPage: (page: number) => string;
  pending?: boolean;
}

export function SearchPagination({ page, pageCount, hrefForPage, pending = false }: SearchPaginationProps) {
  if (pageCount <= 1) return null;
  return (
    <nav className={styles.pagination} aria-label="Search result pages" aria-busy={pending}>
      {page > 1 && !pending ? (
        <Link href={hrefForPage(page - 1)} scroll={false} aria-label="Previous page">
          <LeftOutlined aria-hidden />
        </Link>
      ) : (
        <span aria-disabled="true" aria-label="Previous page"><LeftOutlined aria-hidden /></span>
      )}
      {paginationPages(page, pageCount).map((item) => typeof item === "number" ? pending ? (
        <span key={item} aria-disabled="true" aria-label={`Page ${item}`} aria-current={page === item ? "page" : undefined}>{item}</span>
      ) : (
        <Link
          key={item}
          href={hrefForPage(item)}
          scroll={false}
          aria-label={`Page ${item}`}
          aria-current={page === item ? "page" : undefined}
        >
          {item}
        </Link>
      ) : (
        <span key={item} className={styles.paginationGap} aria-hidden>…</span>
      ))}
      {page < pageCount && !pending ? (
        <Link href={hrefForPage(page + 1)} scroll={false} aria-label="Next page">
          <RightOutlined aria-hidden />
        </Link>
      ) : (
        <span aria-disabled="true" aria-label="Next page"><RightOutlined aria-hidden /></span>
      )}
    </nav>
  );
}
