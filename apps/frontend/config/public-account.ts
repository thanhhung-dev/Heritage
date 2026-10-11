import { PUBLIC_ROUTE_BY_KEY } from "./public-navigation";

export const PUBLIC_ACCOUNT_LINKS = [
  { key: "profile", label: "Hồ sơ", href: null },
  { key: "preferences", label: "Sở thích", href: PUBLIC_ROUTE_BY_KEY.preferences.href },
] as const;
