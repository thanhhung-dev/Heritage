'use client';

import { App } from 'antd';
import {
  type CustomStylishParams,
  type CustomTokenParams,
  type GetAntdTheme,
  ThemeProvider as AntdThemeProvider,
} from 'antd-style';
import { merge } from 'es-toolkit/compat';
import { memo, useCallback, type PropsWithChildren } from 'react';

import { tapestryAntdTheme } from '@/styles/theme/heritageTheme';

import AntdConfigProvider from './ConfigProvider';
import GlobalStyle, { EssentialStyle } from './GlobalStyle';
import { heritageCustomToken } from '@/styles/customToken';
import { HeritageCustomToken } from '@/types/customToken';
import { heritageCustomStylish } from '@/styles/customStylish';

interface ThemeProviderProps extends PropsWithChildren {
  enableGlobalStyle?: boolean;
}

const ThemeProvider = memo<ThemeProviderProps>(
  ({ children, enableGlobalStyle = true }) => {
    const token = useCallback(
      (_t: CustomTokenParams) => heritageCustomToken(),
      [],
    );

    const stylish = useCallback(
      (s: CustomStylishParams) => heritageCustomStylish(s),
      [],
    );

    const theme = useCallback<GetAntdTheme>(
      () => merge({}, tapestryAntdTheme),
      [],
    );

    return (
      <AntdThemeProvider<HeritageCustomToken>
        appearance="dark"
        customToken={token}
        customStylish={stylish}
        theme={theme}
      >
        <AntdConfigProvider>
          <EssentialStyle />
          {enableGlobalStyle && <GlobalStyle />}

          <App style={{ minHeight: '100vh' }}>{children}</App>
        </AntdConfigProvider>
      </AntdThemeProvider>
    );
  },
);

ThemeProvider.displayName = 'HeritageThemeProvider';
export default ThemeProvider;
