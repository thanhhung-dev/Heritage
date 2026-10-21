export interface HeritageSource {
  title: string;
  url: string | null;
  license: string | null;
}

export interface HeritageDetail {
  slug: string;
  locale: string;
  title: string;
  subtitle: string | null;
  region: string;
  location_label: string | null;
  description: string | null;
  hero_image_url: string | null;
  revision: number;
  published_at: string;
  sources: HeritageSource[];
  scene_available: boolean;
}