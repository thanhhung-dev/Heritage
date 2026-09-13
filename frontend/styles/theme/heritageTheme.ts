import type { ThemeConfig } from 'antd';
import { theme as antdAlgo } from 'antd';

export const tapestryAntdTheme: ThemeConfig = {
  algorithm: antdAlgo.darkAlgorithm,
  token: {
    colorPrimary: '#ff9b2d',
    colorInfo: '#ff9b2d',
    colorError: '#e92c42',
    colorSuccess: '#88ba6c',

    colorBgBase: '#0a0e14',
    fontFamily: '"Poppins", sans-serif',
    borderRadius: 12,
    borderRadiusLG: 16,
  },
  components: {
    Button: {
      controlHeight: 40,
      fontWeight: 600,
    },
  },
};
