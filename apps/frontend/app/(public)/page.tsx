import type { Metadata } from "next";
import { FeaturePlaceholder } from "@/components/placeholders/FeaturePlaceholder";
import { PUBLIC_ROUTE_BY_KEY } from "@/config/public-navigation";

const route = PUBLIC_ROUTE_BY_KEY.home;

export const metadata: Metadata = {
  title: route.title,
  description: route.description,
  alternates: { canonical: route.href },
};

export default function HomePage() {
  return <FeaturePlaceholder route={route} />;
}
