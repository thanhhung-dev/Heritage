import { apiClient } from "@/config/api";

export type EntityType = "place" | "artifact" | "collection" | "event" | "person" | "practice";
export type SectionKey = "featured" | "artifacts_treasures" | "people_traditions" | "festivals_practices" | "artifact_collection";
export interface VerifiedFact { value: string; source_url: string }
export interface CatalogContent {
  id: number;
  slug: string;
  title: string;
  description: string | null;
  region: string | null;
  entity_type: EntityType;
  categories: string[];
  primary_category: string;
  card_image_url: string | null;
  source_url: string | null;
  metadata: Partial<Record<"period" | "material" | "origin" | "custodian", VerifiedFact | null>>;
  heritage_id: number | null;
  heritage_slug: string | null;
  href: string;
}
export interface CatalogPage { items: CatalogContent[]; next_offset: number | null }
export type CatalogSections = Record<SectionKey, CatalogPage>;
export interface CatalogDetail extends CatalogContent {
  related_entities: { relation_type: string; content: CatalogContent; source_url: string }[];
}

export function getCatalogSections(signal?: AbortSignal): Promise<CatalogSections> {
  return apiClient("/catalog/sections?limit=8", { cache: "no-store", signal });
}
export function getCatalogSection(section: SectionKey, offset: number): Promise<CatalogPage> {
  return apiClient(`/catalog/sections/${section}?limit=8&offset=${offset}`, { cache: "no-store" });
}
export function getCatalogDetail(slug: string, signal?: AbortSignal): Promise<CatalogDetail> {
  return apiClient(`/catalog/contents/${encodeURIComponent(slug)}`, { cache: "no-store", signal });
}
