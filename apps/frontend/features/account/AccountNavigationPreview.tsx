"use client";

import { useState } from "react";
import { Button, Space } from "antd";
import { AccountNavigation } from "./AccountNavigation";
import type { PublicAccount } from "./types";
import styles from "./account.module.css";

const PREVIEW_ACCOUNT: PublicAccount = { displayName: "Bảo Ngọc", email: "bao.ngoc@example.com" };

export function AccountNavigationPreview() {
  const [account, setAccount] = useState<PublicAccount | null>(PREVIEW_ACCOUNT);

  return (
    <section className={styles.preview} aria-labelledby="account-preview-title">
      <h2 id="account-preview-title">UI tài khoản</h2>
      <p>Bản xem trước Guest và Profile. Thay đổi ở đây chỉ áp dụng cho ví dụ này.</p>
      <Space wrap className={styles.previewActions}>
        <Button onClick={() => setAccount(null)}>Xem Guest</Button>
        <Button onClick={() => setAccount(PREVIEW_ACCOUNT)}>Xem Profile</Button>
      </Space>
      <AccountNavigation
        account={account}
        onSignOut={() => setAccount(null)}
      />
    </section>
  );
}
