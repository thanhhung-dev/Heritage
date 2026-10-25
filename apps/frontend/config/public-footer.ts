import { PUBLIC_NAVIGATION_ITEMS } from "./public-navigation";

export interface FooterLink {
  key: string;
  label: string;
  href: string | null;
}

export const PUBLIC_FOOTER = {
  description:
    "This platform is nothing without its visiting agent. Heal every story you step.",
  groups: [
    {
      key: "about",
      label: "About HERITAGE",
      links: [
        { key: "partners", label: "Partners", href: null },
        { key: "team", label: "Our team", href: null },
        { key: "how-it-works", label: "How it Works", href: null },
        { key: "testimonials", label: "Testimonials", href: null },
        { key: "privacy", label: "Privacy", href: null },
      ] satisfies FooterLink[],
    },
    {
      key: "socials",
      label: "Socials",
      links: [
        { key: "x", label: "X (Twitter)", href: "https://x.com" },
        { key: "linkedin", label: "LinkedIn", href: "https://linkedin.com" },
        { key: "tiktok", label: "TikTok", href: "https://tiktok.com" },
        { key: "instagram", label: "Instagram", href: "https://instagram.com" },
      ] satisfies FooterLink[],
    },
  ],
};

export const PUBLIC_FOOTER_PATHS: readonly string[] = [
  ...PUBLIC_NAVIGATION_ITEMS.map((route) => route.href),
  "/preview",
];
