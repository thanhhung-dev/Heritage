export interface SearchState {
  q: string;
  region: string;
  category: string;
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
}

export interface SearchResults {
  items: HeritageSearchItem[];
  total: number;
  page: number;
  pageCount: number;
  pageSize: number;
  regions: string[];
  categories: string[];
}
