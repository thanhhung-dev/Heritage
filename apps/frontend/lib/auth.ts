/** Authentication utilities for token storage and management. */

export interface User {
  account_id: string;
  email: string;
  username: string;
  role: string;
  /** Display name supplied by the identity provider (e.g. Google). */
  display_name?: string;
  /** Avatar URL supplied by the identity provider (e.g. Google `picture`). */
  avatar_url?: string;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
  user: User;
}

const TOKEN_KEY = 'heritage_access_token';
const USER_KEY = 'heritage_user';

/** Fired in the same tab whenever the stored session changes. */
export const AUTH_CHANGE_EVENT = 'heritage-auth-change';

function notifyAuthChange(): void {
  if (typeof window === 'undefined') return;

  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
}

/**
 * Store authentication token and user info in localStorage
 */
export function setAuthTokens(tokens: AuthTokens): void {
  if (typeof window === 'undefined') return;
  
  localStorage.setItem(TOKEN_KEY, tokens.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(tokens.user));
  notifyAuthChange();
}

/**
 * Get stored access token
 */
export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Get stored user info
 */
export function getUser(): User | null {
  if (typeof window === 'undefined') return null;
  
  const userStr = localStorage.getItem(USER_KEY);
  if (!userStr) return null;
  
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

/**
 * Clear authentication data (logout)
 */
export function clearAuth(): void {
  if (typeof window === 'undefined') return;
  
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  notifyAuthChange();
}

/**
 * Get authorization header for API requests
 */
export function getAuthHeader(): Record<string, string> {
  const token = getAccessToken();
  if (!token) return {};
  
  return {
    Authorization: `Bearer ${token}`,
  };
}
