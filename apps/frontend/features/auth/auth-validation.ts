export type AuthField = "email" | "username" | "password";
export const MIN_PASSWORD_LENGTH = 8;
export const MAX_PASSWORD_LENGTH = 1024;

export function emailError(value: string): string {
  const email = value.trim();
  if (!email) return "Enter your email.";
  if (email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return "Enter a valid email address.";
  return "";
}

export function usernameError(value: string): string {
  const username = value.trim(), length = Array.from(username).length;
  if (!username) return "Enter a username.";
  if (length < 3 || length > 50) return "Username must be between 3 and 50 characters.";
  if (!/^[\p{L}\p{N}_-]+$/u.test(username)) return "Username can only contain letters, numbers, _ and -.";
  return "";
}

export function passwordError(value: string, registering = false): string {
  if (!value) return "Enter your password.";
  const length = Array.from(value).length;
  if (registering && length < MIN_PASSWORD_LENGTH) return "Password must be at least 8 characters.";
  if (length > MAX_PASSWORD_LENGTH) return "Password must be no more than 1024 characters.";
  if (registering && !value.trim()) return "Password cannot contain only spaces.";
  return "";
}

/** Continue only to local application paths supplied by the auth guard. */
export function safeAuthNext(value: string | null): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || /[\\\u0000-\u0020]/.test(value)) return "/";
  const url = new URL(value, "https://heritage.invalid");
  if (url.origin !== "https://heritage.invalid" || /^\/sign-(in|up)(\/|$)/.test(url.pathname)) return "/";
  return url.pathname + url.search + url.hash;
}

export function registrationSignInHref(next: string | null): string {
  const query = new URLSearchParams({ registered: "1" });
  const destination = safeAuthNext(next);
  if (destination !== "/") query.set("next", destination);
  return "/sign-in?" + query.toString();
}
