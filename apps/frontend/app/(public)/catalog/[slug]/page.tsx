import { CatalogDetail } from "@/features/catalog/CatalogDetail";

export default function CatalogContentPage({ params }: { params: { slug: string } }) {
  return <CatalogDetail slug={params.slug} />;
}
