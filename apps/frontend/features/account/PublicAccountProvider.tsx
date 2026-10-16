"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";
import type { PublicAccount } from "./types";

interface PublicAccountState {
  account: PublicAccount | null;
  status: "guest" | "authenticated";
  onSignOut?: () => void;
}

const PublicAccountContext = createContext<PublicAccountState>({
  account: null,
  status: "guest",
});

interface PublicAccountProviderProps {
  children: ReactNode;
  account?: PublicAccount | null;
  onSignOut?: () => void;
}

// Presentation state only. A future session integration owns account updates.
export function PublicAccountProvider({ children, account = null, onSignOut }: PublicAccountProviderProps) {
  const value = useMemo<PublicAccountState>(() => ({
    account,
    status: account ? "authenticated" : "guest",
    onSignOut,
  }), [account, onSignOut]);

  return <PublicAccountContext.Provider value={value}>{children}</PublicAccountContext.Provider>;
}

export function usePublicAccount() {
  return useContext(PublicAccountContext);
}
