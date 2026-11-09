import { apiClient } from "@/config/api";

export interface Voice {
  id: number;
  name: string;
  title: string;
  bio?: string;
  headshot_url?: string;
}

export interface HeritageItem {
  id: number;
  slug: string;
  title: string;
  tagline?: string;
  description: string;
  region: string;
  publish_date?: string;
  card_image_url?: string;
  splash_image_url?: string;
  hover_video_url?: string;
  coverImage?: string;
  language1?: {
    code: string;
    name: string;
  };
  voices?: Voice[];
}

export async function getHeritages(): Promise<HeritageItem[]> {
  return apiClient<HeritageItem[]>("/heritages");
}
