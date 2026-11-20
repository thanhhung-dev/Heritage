"use client";

import { useEffect, useState } from "react";
import { AUTH_CHANGE_EVENT, getAccessToken, getUser, type User } from "../../lib/auth";

export interface AdminSession { status: "checking" | "anonymous" | "forbidden" | "ready"; user: User | null }

/** UX gate only; every library API independently checks current database roles. */
export function useAdminSession(): AdminSession {
  const [session, setSession] = useState<AdminSession>({ status: "checking", user: null });
  useEffect(() => {
    const read = () => {
      const token = getAccessToken(), user = getUser();
      setSession({ user, status: !token ? "anonymous"
        : typeof user?.role !== "string" || user.role.toLowerCase() !== "admin" ? "forbidden" : "ready" });
    };
    read();
    window.addEventListener(AUTH_CHANGE_EVENT, read);
    window.addEventListener("storage", read);
    return () => { window.removeEventListener(AUTH_CHANGE_EVENT, read); window.removeEventListener("storage", read); };
  }, []);
  return session;
}
