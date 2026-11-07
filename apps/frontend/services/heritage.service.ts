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
  language1?: {
    code: string;
    name: string;
  };
  voices?: Voice[];
}

const API_BASE_URL = "https://dev-api.worldheritagea.tech";

export async function getHeritages(): Promise<HeritageItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/heritages`, {
    headers: {
      "Accept": "application/json",
    },
    // cache: "no-store", // Bật nếu muốn data cập nhật liên tục không bị cache
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch heritages: ${res.statusText}`);
  }

  return res.json();
}