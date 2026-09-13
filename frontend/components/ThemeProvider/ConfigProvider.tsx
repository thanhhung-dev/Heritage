'use client';

import { ConfigProvider as AntdConfigProvider } from 'antd';
import { cssVar } from 'antd-style';
import { memo, type PropsWithChildren } from 'react';

const ConfigProvider = memo<PropsWithChildren>(({ children }) => (
  <AntdConfigProvider
    theme={{
      components: {
        Button: { contentFontSizeSM: 12 },
        Input: {
          activeBorderColor: cssVar.colorPrimary,
          hoverBorderColor: cssVar.colorBorder,
        },
        Select: {
          activeBorderColor: cssVar.colorPrimary,
          hoverBorderColor: cssVar.colorBorder,
        },
      },
    }}
  >
    {children}
  </AntdConfigProvider>
));

ConfigProvider.displayName = 'HeritageConfigProvider';
export default ConfigProvider;
