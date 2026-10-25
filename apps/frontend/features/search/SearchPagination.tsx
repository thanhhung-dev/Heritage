import Link from "next/link";
import { LeftOutlined, RightOutlined } from "@ant-design/icons";
import { paginationPages } from "./search-params";
import styles from "./search.module.css";

interface SearchPaginationProps {
  page: number;
  pageCount: number;
  hrefForPage: (page: number) => string;
}

export function SearchPagination({ page, pageCount, hrefForPage }: SearchPaginationProps) {
  if (pageCount <= 1) return null;
  return (
    <nav className={styles.pagination} aria-label="Phân trang kết quả tìm kiếm">
      {page > 1 ? (
        <Link href={hrefForPage(page - 1)} scroll={false} aria-label="Trang trước">
          <LeftOutlined aria-hidden />
        </Link>
      ) : (
        <span aria-disabled="true" aria-label="Trang trước"><LeftOutlined aria-hidden /></span>
      )}
      {paginationPages(page, pageCount).map((item) => typeof item === "number" ? (
        <Link
          key={item}
          href={hrefForPage(item)}
          scroll={false}
          aria-label={`Trang ${item}`}
          aria-current={page === item ? "page" : undefined}
        >
          {item}
        </Link>
      ) : (
        <span key={item} className={styles.paginationGap} aria-hidden>…</span>
      ))}
      {page < pageCount ? (
        <Link href={hrefForPage(page + 1)} scroll={false} aria-label="Trang sau">
          <RightOutlined aria-hidden />
        </Link>
      ) : (
        <span aria-disabled="true" aria-label="Trang sau"><RightOutlined aria-hidden /></span>
      )}
    </nav>
  );
}
