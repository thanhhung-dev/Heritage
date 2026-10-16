export const PUBLIC_AUTH_ROUTES = {
  login: "/sign-in",
  register: "/sign-up",
} as const;

export const PUBLIC_AUTH_PROVIDERS = [
  { key: "google", label: "Google", icon: "/figma/auth-google.svg" },
  { key: "x", label: "X", icon: "/figma/auth-x.svg" },
  { key: "apple", label: "Apple", icon: "/figma/auth-apple.svg" },
  { key: "facebook", label: "Facebook", icon: "/figma/auth-facebook.svg" },
] as const;

// Heritage policy destinations have not been agreed; do not copy the sample Replit URLs.
export const PUBLIC_AUTH_POLICIES: readonly { key: string; label: string; href: string | null }[] = [
  { key: "terms", label: "Terms of Service", href: null },
  { key: "privacy", label: "Privacy Policy", href: null },
] as const;
