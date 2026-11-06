/**
 * Authored search categories for the current published catalogue's exact slugs.
 * The deployed HeritageOut has no category yet. An API category always wins;
 * unlisted sites remain uncategorized. Never infer categories from title text.
 */
export const DESIGN_CATEGORIES = [
  "Imperial & Historic Relics",
  "Temples, Pagodas",
  "Natural Landscapes & Scenic Sites",
  "Traditional Craft Villages & Living Heritage",
  "Museums & Antiquities",
] as const;

type HeritageCategory = typeof DESIGN_CATEGORIES[number];
const [historic, temples, landscapes, livingHeritage, museums] = DESIGN_CATEGORIES;

const catalogueCategories: Readonly<Record<string, HeritageCategory>> = {
  "lang-tu-duc": historic,
  "lang-minh-mang": historic,
  "lang-gia-long": historic,
  "lang-khai-dinh": historic,
  "cung-an-dinh": historic,
  "cong-ngo-mon": historic,
  "dai-noi-hue": historic,
  "chua-thien-mu": temples,
  "chua-huyen-khong-son-thuong": temples,
  "dien-hon-chen": temples,
  "lang-sinh": livingHeritage,
  "cau-ngoi-thanh-toan": historic,
  "lang-thieu-tri": historic,
  "lang-dong-khanh": historic,
  "cuu-dinh": museums,
  "cau-truong-tien": historic,
  "cho-dong-ba": livingHeritage,
  "chua-linh-ung-son-tra": temples,
  "bao-tang-dieu-khac-cham": museums,
  "ngu-hanh-son": landscapes,
  "dinh-lang-tuy-loan": historic,
  "dinh-lang-nam-o": historic,
  "ban-dao-son-tra": landscapes,
  "ba-na-hills": landscapes,
  "lang-da-non-nuoc": livingHeritage,
  "pho-co-hoi-an": historic,
  "lang-gom-thanh-ha": livingHeritage,
  "thanh-dia-my-son": historic,
};

export function heritageCategory(slug: string, apiCategory?: string | null): string | null {
  return apiCategory?.trim() || (Object.hasOwn(catalogueCategories, slug) ? catalogueCategories[slug] : null);
}
