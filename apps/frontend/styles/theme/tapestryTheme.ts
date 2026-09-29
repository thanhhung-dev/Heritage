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