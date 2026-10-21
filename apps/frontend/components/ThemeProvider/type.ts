import type { SerializedStyles } from '@emotion/react';
import type {
  ThemeProviderProps as AntdThemeProviderProps,
  CustomStylishParams,
  CustomTokenParams,
} from 'antd-style';
import type { CSSProperties } from 'react';

import type { NeutralColors, PrimaryColors } from '@/styles';

type CustomStylish = Record<string, SerializedStyles>;
type CustomToken = Record<string, unknown>;

export interface ThemeProviderProps extends AntdThemeProviderProps<CustomToken, CustomStylish> {
  className?: string;
  customFonts?: string[];
  customStylish?: (theme: CustomStylishParams) => CustomStylish;
  customTheme?: {
    neutralColor?: NeutralColors;
    primaryColor?: PrimaryColors;
  };
  customToken?: (theme: CustomTokenParams) => CustomToken;
  enableCustomFonts?: boolean;
  enableGlobalStyle?: boolean;
  style?: CSSProperties;
}

export interface MetaProps {
  description?: string;
  title?: string;
  withManifest?: boolean;
}