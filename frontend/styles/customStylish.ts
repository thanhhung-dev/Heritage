import { CustomStylishParams } from 'antd-style';

export const heritageCustomStylish = ({ css, token }: CustomStylishParams) => ({
  glassPanel: css`
    background: ${token.glassBg};
    backdrop-filter: ${token.glassBlur};
    -webkit-backdrop-filter: ${token.glassBlur};
    border: 1px solid ${token.glassBorder};
  `,

  gradientButton: css`
    color: #fff;
    border: none;
    border-radius: 20px;
    background: ${token.gradientPrimary};
    box-shadow: ${token.shadowGlow};
    transition: all 0.3s ease;

    &:hover {
      background: ${token.gradientPrimaryHover};
      transform: translateY(-2px);
    }
  `,
});
