import { css, type Theme } from 'antd-style';

export default (token: Theme) => css`
  /* Helper hiển thị */
  .tapestry-hidden {
    display: none !important;
  }

  .tapestry-unselectable {
    user-select: none;
    -webkit-user-select: none;
    -webkit-touch-callout: none;
  }

  @keyframes tapestryGlow {
    0%,
    100% {
      box-shadow: 0 0 6px 1px rgba(255, 155, 45, 0.2);
      transform: scale(1);
    }
    50% {
      box-shadow: 0 0 12px 4px rgba(255, 155, 45, 0.6);
      transform: scale(1.04);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
      animation-duration: 0.01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important;
      scroll-behavior: auto !important;
    }
  }
`;
