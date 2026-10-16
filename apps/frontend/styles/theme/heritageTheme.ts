import type { CSSProperties } from "react";
import type { ThemeConfig } from "antd";

export const tapestryColors = {
  background: "#0a0e14",
  surface: "#14181f",
  surfaceHover: "#1c212b",
  text: "#f0e8dd",
  textMuted: "rgba(240, 232, 221, 0.5)",
  textFaint: "rgba(240, 232, 221, 0.3)",
  primary: "#FF9B2D",
  primaryHover: "#ffb04f",
  primaryPress: "#e88010",
  border: "rgba(240, 232, 221, 0.12)",
  borderStrong: "rgba(240, 232, 221, 0.2)",
  error: "#ea3241",
};

/**
 * Heritage viewer (3D tour) design tokens — CyArk Tapestry aliases.
 *
 * These live here (single source of truth) and are injected by
 * `HeritageViewer` as CSS custom properties on its root, replacing the
 * hard-coded `:root` block previously inside `styles.module.css`.
 */
export const tapestryTourVars: Record<string, string> = {
  "--orange-to-white": tapestryColors.primary,
  "--UI-color-orange": tapestryColors.primary,
  "--white-to-black": "#ffffff",
  "--title": tapestryColors.text,
  "--subTitle": tapestryColors.textMuted,
  "--text": "rgba(240, 232, 221, 0.65)",
  "--gd-media-strip-bg": "#1c1b1acc",
  "--gd-stop-nav-bg": "#1c1b1a80",
  "--gd-button-hover": "#302e2ce6",
  "--gd-light-button-background": "#f0e8dd1a",
  "--gd-accent-red-background": "#ea324133",
  "--bg-bleng-none-to-color": "unset",
  "--black-opacity-0": "#00000000",
  "--black-opacity-10": "#0000001a",
  "--black-opacity-20": "#00000033",
  "--black-opacity-30": "#0000004d",
  "--black-opacity-40": "#00000066",
  "--black-opacity-50": "#00000080",
  "--black-opacity-60": "#00000099",
  "--black-opacity-70": "#000000b3",
  "--black-opacity-80": "#000000cc",
  "--black-opacity-90": "#000000e6",
  "--white-opacity-90": "#ffffffe6",
  "--white-opacity-6": "#ffffff0f",
  "--opacity-055": "0.55",
  "--opacity-06": "0.6",
  "--opacity-07": "0.7",
  "--font-size-14": "14px",
  "--font-size-13": "13px",
  "--font-size-12": "12px",
  "--font-size-11": "11px",
  "--font-size-10": "10px",
  "--font-size-9": "9px",
  "--font-size-8": "8px",
  "--zoom-value": "1",
  "--app-height": "100%",
  "--footer-bottom": "0",
};

export const tapestryTourVarsStyle = tapestryTourVars as CSSProperties;

/** High-contrast overrides applied when `data-theme="high-contrast"`. */
export const tapestryTourHighContrastVars: Partial<Record<string, string>> = {
  "--orange-to-white": "#ffffff",
  "--white-to-black": "#000000",
  "--gd-media-strip-bg": "#000000",
  "--gd-stop-nav-bg": "#000000",
  "--gd-button-hover": "#000000",
  "--gd-light-button-background": "#000000",
  "--gd-accent-red-background": "#54171c",
  "--title": "#ffffff",
  "--subTitle": "#ffffff",
  "--text": "#ffffff",
  "--bg-bleng-none-to-color": "color",
};

export const tapestryTheme: ThemeConfig = {
  token: {
    colorPrimary: tapestryColors.primary,
    colorInfo: tapestryColors.primary,
    colorLink: tapestryColors.primary,
    colorLinkHover: tapestryColors.primaryHover,
    colorSuccess: "#16a34a",
    colorWarning: "#b07d1a",
    colorError: tapestryColors.error,
    colorBgBase: tapestryColors.background,
    colorBgLayout: tapestryColors.background,
    colorBgContainer: tapestryColors.surface,
    colorBgElevated: tapestryColors.surfaceHover,
    colorTextBase: tapestryColors.text,
    colorText: "rgba(240, 232, 221, 0.85)",
    colorTextSecondary: tapestryColors.textMuted,
    colorTextTertiary: tapestryColors.textFaint,
    colorBorder: tapestryColors.border,
    colorBorderSecondary: tapestryColors.border,
    borderRadius: 10,
    fontFamily: "'Poppins', sans-serif",
  },
  components: {
    Menu: {
      itemSelectedBg: "rgba(255, 155, 45, 0.15)",
      itemSelectedColor: tapestryColors.primary,
      itemHoverBg: "rgba(240, 232, 221, 0.06)",
      itemBg: "transparent",
      subMenuItemBg: "transparent",
      itemBorderRadius: 8,
    },
    Layout: {
      headerBg: tapestryColors.surface,
      siderBg: tapestryColors.surface,
      bodyBg: tapestryColors.background,
    },
    Button: {
      fontWeight: 600,
    },
  },
};