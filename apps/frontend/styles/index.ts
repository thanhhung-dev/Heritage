import type {
  CustomStylishParams,
  CustomTokenParams,
} from "antd-style";
import type { ThemeConfig } from "antd";

import { createLobeAntdTheme } from "./theme/antdTheme";
import { NeutralColors, PrimaryColors } from "./customTheme";
import type { LobeCustomToken } from "@/types/customToken";

export * from "./customTheme";

export interface LobeCustomTokenParams extends CustomTokenParams {}

export const lobeCustomToken = (_theme: LobeCustomTokenParams) => {
  return {
    headerHeight: 64,
    colorText: "#fff",
  } satisfies LobeCustomToken;
};

export const lobeCustomStylish = (_theme: CustomStylishParams) => {
  return {};
};

export const createAntdTheme = (options: {
  appearance: string;
  neutralColor?: NeutralColors;
  primaryColor?: PrimaryColors;
}): ThemeConfig => createLobeAntdTheme(options);

export { createLobeAntdTheme };