import type { HeritageCustomToken } from '@/types/customToken';

declare module 'antd-style' {
  export interface CustomToken extends HeritageCustomToken {}

  export interface CustomStylish {
    glassPanel: import('@emotion/serialize').SerializedStyles;
    gradientButton: import('@emotion/serialize').SerializedStyles;
  }
}
