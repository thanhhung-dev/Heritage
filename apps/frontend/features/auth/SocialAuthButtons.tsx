"use client";

import { useState } from "react";
import Image from "next/image";
import { Button } from "antd";
import { PUBLIC_AUTH_PROVIDERS } from "@/config/public-auth";
import styles from "./auth.module.css";

export function SocialAuthButtons() {
  const [notice, setNotice] = useState("");

  return (
    <div>
      <div className={styles.providers} aria-label="Continue with a social account" role="group">
        {PUBLIC_AUTH_PROVIDERS.map((provider) => (
          <Button key={provider.key} className={styles.providerButton} onClick={() => setNotice(`${provider.label} sign-in is currently unavailable. Please try again later.`)}>
            <Image src={provider.icon} alt="" aria-hidden="true" width={20} height={20} />
            <span>Continue with {provider.label}</span>
          </Button>
        ))}
      </div>
      <p role="status" aria-live="polite" className={notice ? styles.notice : styles.srOnly}>{notice}</p>
    </div>
  );
}
