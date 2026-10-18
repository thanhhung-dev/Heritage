import { PUBLIC_SHELL_PATHS } from "./public-navigation";

export interface FooterLink {
  key: string;
  label: string;
  href: string | null;
}

// Unconfirmed destinations remain text until their URLs are approved.
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
        { key: "x", label: "X (Twitter)", href: null },
        { key: "linkedin", label: "LinkedIn", href: null },
        { key: "tiktok", label: "TikTok", href: null },
        { key: "instagram", label: "Instagram", href: null },
      ] satisfies FooterLink[],
    },
  ],
};

export const PUBLIC_FOOTER_PATHS = PUBLIC_SHELL_PATHS;
