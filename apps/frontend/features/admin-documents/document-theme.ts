import { theme, type ThemeConfig } from "antd";

/** Ant Design seed for the light document workspace shown in the admin design. */
export const documentTheme: ThemeConfig = {
  inherit: false,
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: "#201F1C",
    colorText: "#201F1C",
    colorTextSecondary: "#928F86",
    colorTextLightSolid: "#FFFFFF",
    colorLink: "#201F1C",
    colorLinkHover: "#55524C",
    colorBgContainer: "#FFFFFF",
    colorBorder: "#E5E4E0",
    borderRadius: 8,
    fontFamily: "Roboto, Arial, sans-serif",
  },
  components: {
    Button: { primaryColor: "#FFFFFF" },
    Table: { headerBg: "#FAFAF9", rowHoverBg: "#F5F4F2" },
  },
};
