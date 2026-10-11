"use client";

import { useCallback, useState } from "react";
import { Button, Space } from "antd";
import { AccountNavigation } from "./AccountNavigation";
import { PublicHeaderControls } from "@/components/public-shell/PublicHeaderControls";
import { PublicAccountProvider, usePublicAccount } from "./PublicAccountProvider";
import type { PublicAccount } from "./types";
import styles from "./account.module.css";

const PREVIEW_ACCOUNT: PublicAccount = { displayName: "Bảo Ngọc" };
const LONG_NAME_ACCOUNT: PublicAccount = { displayName: "Bảo Ngọc — Người yêu di sản văn hóa Đà Nẵng và Huế" };

function PreviewStatus() {
  const { status } = usePublicAccount();
  return <p role="status" className={styles.previewStatus}>Trạng thái mẫu: {status === "guest" ? "Guest" : "Authenticated"}</p>;
}

export function AccountNavigationPreview() {
  const [account, setAccount] = useState<PublicAccount | null>(PREVIEW_ACCOUNT);
  const signOut = useCallback(() => setAccount(null), []);

  return (
    <section className={styles.preview} aria-labelledby="account-preview-title">
      <h2 id="account-preview-title">UI tài khoản</h2>
      <p>Bản xem trước Guest và Profile. Thay đổi ở đây chỉ áp dụng cho ví dụ này.</p>
      <Space wrap className={styles.previewActions}>
        <Button onClick={() => setAccount(null)}>Xem Guest</Button>
        <Button onClick={() => setAccount(PREVIEW_ACCOUNT)}>Xem Profile</Button>
        <Button onClick={() => setAccount(LONG_NAME_ACCOUNT)}>Xem tên dài</Button>
      </Space>
      <PublicAccountProvider account={account} onSignOut={signOut}>
        <PreviewStatus />
        <div className={styles.previewHeader} aria-label="Bản mẫu navigation và tài khoản">
          <PublicHeaderControls />
        </div>
        <div className={styles.previewAccount} aria-label="Bản mẫu menu tài khoản">
          <AccountNavigation />
        </div>
      </PublicAccountProvider>
    </section>
  );
}
