import type { Metadata } from "next";
import { FeaturePlaceholder } from "@/components/placeholders/FeaturePlaceholder";
import { PUBLIC_ROUTE_BY_KEY } from "@/config/public-navigation";

const route = PUBLIC_ROUTE_BY_KEY.explore;

export const metadata: Metadata = {
  title: route.title,
  description: route.description,
  alternates: { canonical: route.href },
};

export default function ExplorePage({
  searchParams,
}: {
  searchParams?: { q?: string | string[] };
}) {
  const rawQuery = searchParams?.q;
  const query = (Array.isArray(rawQuery) ? rawQuery[0] : rawQuery)?.trim();
  const pageRoute = query
    ? {
        ...route,
        title: `Tìm kiếm: ${query}`,
        description: `Kết quả cho “${query}” sẽ có khi bộ sưu tập di sản được kết nối.`,
      }
    : route;

  return <FeaturePlaceholder route={pageRoute} />;
}
