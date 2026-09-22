"use client";

import { SettingOutlined, QuestionCircleOutlined } from "@ant-design/icons";

export function TopBar() {
  return (
    <div className="topbar">
      <div className="topbar-actions">
        <button className="btn-icon" aria-label="Cài đặt">
          <SettingOutlined style={{ fontSize: 18 }} />
        </button>
        <button className="btn-icon" aria-label="Quyền riêng tư">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
            <path d="M22 13.5V10.5L18.6914 8.13674L18.2991 4.08973L15.701 2.58973L12 4.27343L8.29904 2.58975L5.70096 4.08975L5.3086 8.13672L2 10.5V12V13.5L5.30858 15.8633L5.70095 19.9103L8.29903 21.4103L12 19.7266L15.701 21.4103L18.299 19.9103L18.6914 15.8633L22 13.5Z" strokeLinecap="square" />
            <path d="M15 12C15 13.6569 13.6569 15 12 15C10.3431 15 9 13.6569 9 12C9 10.3431 10.3431 9 12 9C13.6569 9 15 10.3431 15 12Z" />
          </svg>
        </button>
      </div>
      <div className="topbar-auth">
        <button className="btn-ghost">Đăng nhập</button>
        <button className="btn-primary">Đăng ký</button>
      </div>
    </div>
  );
}

export function HelpButton() {
  return (
    <button className="help-btn" aria-label="Trợ giúp">
      <QuestionCircleOutlined />
    </button>
  );
}
