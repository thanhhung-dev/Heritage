import { css, type Theme } from 'antd-style';
import { rgba } from 'polished';

export default (token: Theme) => {
  const p = token.prefixCls; 

  return css`
    @property --btn-grad-from {
      syntax: '<color>';
      inherits: false;
      initial-value: #ff9b2d;
    }

    @property --btn-grad-to {
      syntax: '<color>';
      inherits: false;
      initial-value: #f07847;
    }

    .${p}-btn {
      box-shadow: none;
    }

    .${p}-btn-primary:not(:disabled) {
      color: #fff !important;
      background: linear-gradient(135deg, var(--btn-grad-from) 0%, var(--btn-grad-to) 100%) !important;
      box-shadow: 0 4px 16px ${rgba(token.colorPrimary, 0.4)};
      border: none;
      transition:
        --btn-grad-from 0.3s ease,
        --btn-grad-to 0.3s ease,
        box-shadow 0.3s ease,
        transform 0.3s ease;

      &:hover {
        --btn-grad-from: #ffab4d;
        --btn-grad-to: #f58857;
        box-shadow: 0 6px 24px ${rgba(token.colorPrimary, 0.5)};
        transform: translateY(-2px);
      }

      &:active {
        transform: translateY(0);
      }
    }

    .${p}-dropdown-menu,
    .${p}-select-dropdown {
      border-radius: ${token.borderRadius}px !important;
      box-shadow:
        0 0 15px 0 rgba(0, 0, 0, 0.2),
        0 2px 30px 0 rgba(0, 0, 0, 0.25),
        0 0 0 1px ${token.colorFillTertiary} inset !important;
    }

    .${p}-modal-content {
      border: 1px solid ${token.colorBorderSecondary} !important;
      border-radius: ${token.borderRadiusLG}px !important;
    }

    .${p}-tooltip {
      --antd-arrow-background-color: ${token.colorBgElevated};
      max-width: 320px;
    }

    .${p}-tooltip-inner {
      border: 1px solid ${token.colorBorderSecondary} !important;
      border-radius: ${token.borderRadiusSM}px !important;
      font-size: ${token.fontSizeSM}px;
      background: ${token.colorBgElevated} !important;
    }

    .${p}-input:focus,
    .${p}-input-focused {
      border-color: ${token.colorPrimary} !important;
      box-shadow: 0 0 0 2px ${rgba(token.colorPrimary, 0.15)} !important;
    }
  `;
};
