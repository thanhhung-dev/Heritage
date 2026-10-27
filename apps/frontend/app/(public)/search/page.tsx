import type { Metadata } from "next";
import { Suspense } from "react";
import { HeritageSearchPage } from "@/features/search/HeritageSearchPage";
import { SearchResultsSkeleton } from "@/features/search/SearchResultsGrid";

export const metadata: Metadata = {
  title: "Tìm kiếm di sản | Heritage",
  description: "Tìm kiếm và khám phá di sản Đà Nẵng – Huế theo từ khóa, vùng miền và danh mục.",
  alternates: { canonical: "/search" },
};

export default function SearchPage() {
  return (
    <Suspense fallback={<SearchResultsSkeleton />}>
      <HeritageSearchPage />
    </Suspense>
  );
}
