import type { Metadata } from "next";
import { Suspense } from "react";
import { HeritageSearchPage } from "@/features/search/HeritageSearchPage";
import { SearchPageSkeleton } from "@/features/search/SearchPageSkeleton";

export const metadata: Metadata = {
  title: "Virtual Tours Search | HERITAGE",
  description: "Discover immersive heritage tours. Search and filter by category, location and historic site.",
  alternates: { canonical: "/search" },
};

export default function SearchPage() {
  return (
    <Suspense fallback={<SearchPageSkeleton />}>
      <HeritageSearchPage />
    </Suspense>
  );
}
