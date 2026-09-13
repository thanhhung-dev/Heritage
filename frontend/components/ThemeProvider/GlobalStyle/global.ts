import { css, type Theme } from 'antd-style';

export default (token: Theme) => css`
  html {
    scroll-behavior: smooth;
    overscroll-behavior: none;
    color-scheme: dark;
  }

  body {
    overflow: hidden auto;
    min-height: 100vh;
    margin: 0;
    padding: 0;

    font-family: ${token.fontFamily};
    font-size: ${token.fontSize}px;
    line-height: 1.5;
    color: ${token.colorText};

    background-color: ${token.colorBgLayout};

    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    -webkit-tap-highlight-color: transparent;
    text-rendering: optimizeLegibility;
  }

  * {
    box-sizing: border-box;
  }

  * {
    scrollbar-width: thin;
    scrollbar-color: rgba(240, 232, 221, 0.35) transparent;
  }

  *::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }

  *::-webkit-scrollbar-track {
    background: rgba(14, 12, 10, 0.35);
    border-radius: 99px;
  }

  *::-webkit-scrollbar-thumb {
    background: rgba(240, 232, 221, 0.35);
    border-radius: 99px;
    transition: background 0.2s ease;
  }

  *::-webkit-scrollbar-thumb:hover {
    background: ${token.colorPrimary};
  }

  a {
    color: ${token.colorPrimary};
    text-decoration: none;
  }

  ::selection {
    color: #000;
    background: ${token.colorPrimary};
  }
`;
