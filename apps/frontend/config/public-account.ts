import { PUBLIC_ROUTE_BY_KEY } from "./public-navigation";

export const PUBLIC_ACCOUNT_LINKS = [
  { key: "profile", label: "Account Profile", href: null, icon: "profile" },
  { key: "help", label: "Help Center", href: PUBLIC_ROUTE_BY_KEY.faq.href, icon: "help" },
  { key: "language", label: "Language", href: null, icon: "language" },
] as const;
