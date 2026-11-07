import googleIcon from "@/access/icons/auth-google.svg";
import githubIcon from "@/access/icons/auth-github.svg";
import xIcon from "@/access/icons/auth-x.svg";
import appleIcon from "@/access/icons/auth-apple.svg";
import facebookIcon from "@/access/icons/auth-facebook.svg";

export const PUBLIC_AUTH_ROUTES = {
  login: "/sign-in",
  register: "/sign-up",
} as const;

export const PUBLIC_AUTH_PROVIDERS = [
  { key: "google", label: "Google", icon: googleIcon },
  { key: "github", label: "GitHub", icon: githubIcon },
  { key: "x", label: "X", icon: xIcon },
  { key: "apple", label: "Apple", icon: appleIcon },
  { key: "facebook", label: "Facebook", icon: facebookIcon },
] as const;

// Heritage policy destinations have not been agreed; do not copy the sample Replit URLs.
export const PUBLIC_AUTH_POLICIES: readonly { key: string; label: string; href: string | null }[] = [
  { key: "terms", label: "Terms of Service", href: null },
  { key: "privacy", label: "Privacy Policy", href: null },
] as const;
