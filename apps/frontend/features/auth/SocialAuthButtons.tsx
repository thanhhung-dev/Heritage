"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Button, message as antdMessage } from "antd";
import { PUBLIC_AUTH_PROVIDERS } from "@/config/public-auth";
import { loadGoogleScript, openGooglePopup } from "@/lib/googleAuth";
import { handleGoogleLogin } from "@/services/authService";
import styles from "./auth.module.css";

export function SocialAuthButtons() {
  const router = useRouter();
  const [loadingProvider, setLoadingProvider] = useState<string | null>(null);
  const [googleReady, setGoogleReady] = useState(false);
  const initRef = useRef(false);

  // Load OAuth scripts on mount
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    // Load Google script
    loadGoogleScript()
      .then(() => setGoogleReady(true))
      .catch((error) => {
        console.error("Failed to load Google script:", error);
      });
  }, []);

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
          await handleGoogleLogin(credential, () => {
            router.push("/");
          });
          setLoadingProvider(null);
        },
        (error) => {
          // Handle Google login error
          console.error("Google login error:", error);
          setLoadingProvider(null);
        }
      );
    } catch (error) {
      console.error("Failed to open Google popup:", error);
      setLoadingProvider(null);
    }
  };

  const handleOtherProviderClick = (providerName: string) => {
    antdMessage.info(`${providerName} login is coming soon.`);
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
            onClick = () => handleOtherProviderClick(provider.label);
            disabled = loadingProvider !== null;
          }
          
          return (
            <Button
              key={provider.key}
              className={styles.providerButton}
              onClick={onClick}
              disabled={disabled}
              loading={isLoading}
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
    </div>
  );
}
