export interface SearchState {
  q: string;
  regions: string[];
  categories: string[];
  locations: string[];
  page: number;
}

export interface HeritageSearchItem {
  id: number;
  slug: string;
  title: string;
  description: string | null;
  tagline: string | null;
  region: string | null;
  category: string | null;
  card_image_url: string | null;
  duration_seconds: number | null;
  headline?: string | null;
  splash_image_url?: string | null;
  language1?: { code: string; name: string } | null;
  language2?: { code: string; name: string } | null;
}

export interface SearchFacet {
  value: string;
  label: string;
  count: number;
}

export interface SearchLocationGroup extends SearchFacet {
  sites: SearchFacet[];
}

export interface SearchResults {
  items: HeritageSearchItem[];
  total: number;
  page: number;
  pageCount: number;
  pageSize: number;
  categoryFacets: SearchFacet[];
  locationGroups: SearchLocationGroup[];
  recommendations: HeritageSearchItem[];
  heroImage: string | null;
  heroFallbackImages: string[];
}
