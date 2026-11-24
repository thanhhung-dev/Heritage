import { API_BASE_URL } from "@/config/api";

const KEY = "heritage_admin_access_token";

export function adminToken(): string | null {
  return sessionStorage.getItem(KEY) || localStorage.getItem(KEY);
}

export function clearAdminSession() {
  sessionStorage.removeItem(KEY);
  localStorage.removeItem(KEY);
}

export function saveAdminSession(value: unknown, remember: boolean): boolean {
  if (!value || typeof value !== "object") return false;
  const result = value as { access_token?: unknown; user?: { role?: unknown } };
  if (typeof result.access_token !== "string" || !result.access_token || typeof result.user?.role !== "string" || result.user.role.toLowerCase() !== "admin") return false;
  clearAdminSession();
  (remember ? localStorage : sessionStorage).setItem(KEY, result.access_token);
  return true;
}

export async function verifyAdmin(token: string, signal?: AbortSignal): Promise<"allowed" | "unauthorized" | "forbidden" | "unavailable"> {
  try {
    const response = await fetch(`${API_BASE_URL}/auth/me`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store", signal });
    if (response.status === 401) return "unauthorized";
    if (response.status === 403) return "forbidden";
    if (!response.ok) return "unavailable";
    const user: unknown = await response.json();
    if (!user || typeof user !== "object" || !("role" in user) || typeof user.role !== "string") return "unavailable";
    return user.role.toLowerCase() === "admin" ? "allowed" : "forbidden";
  } catch { return "unavailable"; }
}

export async function signOutAdmin(): Promise<boolean> {
  const token = adminToken();
  try {
    if (!token) return true;
    const response = await fetch(`${API_BASE_URL}/admin/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
    return response.ok;
  } catch { return false; }
  finally { clearAdminSession(); }
}
