import type { ThemeConfig } from "antd";
import { theme } from "antd";

import { neutralColors, primaryColors } from "../customTheme";
import type { NeutralColors, PrimaryColors } from "../customTheme";

const { darkAlgorithm, defaultAlgorithm } = theme;

interface CreateLobeAntdThemeConfig {
  appearance: string;
  neutralColor?: NeutralColors;
  primaryColor?: PrimaryColors;
}

const buildAlgorithm = (appearance: string) =>
  appearance === "dark" ? darkAlgorithm : defaultAlgorithm;

const colorFrom = (map: Record<string, string>, value?: string) =>
  value ? map[value] : undefined;

export const createLobeAntdTheme = ({
  appearance,
  neutralColor,
  primaryColor,
}: CreateLobeAntdThemeConfig): ThemeConfig => {
  const colorPrimary = primaryColor
    ? primaryColors[primaryColor]
    : undefined;

  return {
    algorithm: buildAlgorithm(appearance),
    token: {
      colorPrimary,
      colorInfo: colorPrimary,
      colorTextBase: neutralColor ? neutralColors[neutralColor] : undefined,
      colorBgBase: neutralColor ? neutralColors[neutralColor] : undefined,
    },
  };
};