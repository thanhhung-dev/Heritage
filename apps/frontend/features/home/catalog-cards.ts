import type { CatalogContent, CatalogPage } from "../../services/catalog.service";
import type { HeritageItem } from "./HeritageCarouselSection";

export function toCatalogCard(item: CatalogContent): HeritageItem {
  return {
    slug: item.slug, title: item.title, description: item.description,
    region: item.region, card_image_url: item.card_image_url, href: item.href,
    language_label: "", published: item.metadata.period?.value ?? null,
  };
}

export function appendCatalogPage(current: CatalogPage, next: CatalogPage): CatalogPage {
  const existing = new Set(current.items.map((item) => item.id));
  return { items: [...current.items, ...next.items.filter((item) => !existing.has(item.id))],
    next_offset: next.next_offset };
}
