"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Button, message as antdMessage } from "antd";
import { PUBLIC_AUTH_PROVIDERS } from "@/config/public-auth";
import { loadGoogleScript, openGooglePopup } from "@/lib/googleAuth";
import { handleGoogleLogin } from "@/services/authService";
import styles from "./auth.module.css";
import { safeAuthNext } from "./auth-validation";

export function SocialAuthButtons() {
  const router = useRouter();
  const [loadingProvider, setLoadingProvider] = useState<string | null>(null);
  const [googleReady, setGoogleReady] = useState(false);
  const initRef = useRef(false);
  const googleConfigured = Boolean(process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID);

  // Load OAuth scripts on mount
  useEffect(() => {
    if (initRef.current || !googleConfigured) return;
    initRef.current = true;

    // Load Google script
    loadGoogleScript()
      .then(() => setGoogleReady(true))
      .catch((error) => {
        console.error("Failed to load Google script:", error);
      });
  }, [googleConfigured]);

  const handleGoogleClick = async () => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    
    if (!clientId) {
      console.error("Google Client ID not configured");
      antdMessage.error("Google login is not configured.");
      return;
    }

    if (!googleReady) {
      console.error("Google script not loaded yet");
      antdMessage.warning("Google login is still loading. Please try again.");
      return;
    }

    setLoadingProvider("google");

    try {
      await openGooglePopup(
        clientId,
        async (credential) => {
          // Handle successful Google login
          setLoadingProvider("google");
          try {
            await handleGoogleLogin(credential, () => {
              router.push(safeAuthNext(new URLSearchParams(window.location.search).get("next")));
            });
          } catch { /* The auth helper has already displayed an actionable error. */ }
          finally { setLoadingProvider(null); }
        },
        (error) => {
          // Handle Google login error
          console.error("Google login error:", error);
          setLoadingProvider(null);
        }
      );
      // One Tap returns after displaying its prompt, rather than after login.
      // A dismissed prompt must not leave this button permanently loading.
      setLoadingProvider(null);
    } catch (error) {
      console.error("Failed to open Google popup:", error);
      setLoadingProvider(null);
    }
  };

  return (
    <div className={styles.socialSection}>
      <div className={styles.providers} aria-label="Continue with a social account" role="group">
        {PUBLIC_AUTH_PROVIDERS.filter((provider) => !["apple", "x"].includes(provider.key)).map((provider) => {
          const isGoogle = provider.key === "google";
          const isLoading = loadingProvider === provider.key;
          
          let onClick: (() => void) | undefined = undefined;
          let disabled = false;
          
          if (isGoogle) {
            onClick = handleGoogleClick;
            disabled = !googleReady || loadingProvider !== null;
          } else {
            // These providers are not wired up yet.
            disabled = true;
          }
          
          return (
            <Button
              key={provider.key}
              className={styles.providerButton}
              onClick={onClick}
              disabled={disabled}
              loading={isLoading}
              title={!isGoogle ? `${provider.label} sign-in is not available yet.` : !googleConfigured ? "Google sign-in is unavailable. Use email and password." : undefined}
            >
              <Image
                src={provider.icon}
                alt=""
                aria-hidden="true"
                width={20}
                height={20}
                className={provider.key === "google" ? undefined : styles.providerIconMono}
              />
              <span>Continue with {provider.label}</span>
            </Button>
          );
        })}
      </div>
      {!googleConfigured && <p className={styles.hint}>Social sign-in is unavailable. Use your email and password.</p>}
    </div>
  );
}
