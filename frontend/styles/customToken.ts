import type { HeritageCustomToken } from "@/types/customToken";

export const heritageCustomToken = (): HeritageCustomToken => ({
  colorAccentDeep: "#f07847",
  gradientPrimary:
    "linear-gradient(135deg, #ff9b2d 0%, #f07847 100%)",
  gradientPrimaryHover:
    "linear-gradient(135deg, #ffab4d 0%, #f58857 100%)",
  colorTitle: "#f0e8dd",
  colorDonate: "#e92c42",
  glassBg: "rgba(255,255,255,0.12)",
  glassBorder: "rgba(255,255,255,0.15)",
  glassBlur: "blur(12px) saturate(1.3)",
  shadowGlow: "0 4px 16px rgba(255,155,45,0.4)",
});