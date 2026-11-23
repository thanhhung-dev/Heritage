import { API_BASE_URL } from "../config/api";
import type { User } from "../lib/auth";
import type { AuthField } from "../features/auth/auth-validation";

export interface RegisterData { email: string; username: string; password: string }
export interface LoginData { email: string; password: string }
export interface RegisterResponse { account_id: string; email: string; username: string; message: string }
export interface LoginResponse { access_token: string; token_type: string; user: User }
export type AuthFieldErrors = Partial<Record<AuthField, string>>;

export class AuthApiError extends Error {
  constructor(message: string, public readonly status: number, public readonly fields: AuthFieldErrors = {}) {
    super(message); this.name = "AuthApiError";
  }
}
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);
const nonempty = (value: unknown): value is string => typeof value === "string" && !!value.trim();

export function authResponseError(data: unknown, status: number): AuthApiError {
  const fields: AuthFieldErrors = {};
  const detail = record(data) ? data.detail : undefined;
  const messages: string[] = [];
  if (Array.isArray(detail)) for (const issue of detail) {
    if (!record(issue) || !nonempty(issue.msg)) continue;
    const field: unknown = Array.isArray(issue.loc) ? issue.loc.at(-1) : undefined;
    const text = issue.msg.replace(/^Value error, /, "");
    if (field === "email" || field === "username" || field === "password") {
      fields[field] ??= text;
      messages.push(`${field[0].toUpperCase() + field.slice(1)}: ${text}`);
    } else messages.push(text);
  }
  const message = typeof detail === "string" && detail.trim() ? detail
    : record(detail) && nonempty(detail.message) ? detail.message
    : record(data) && nonempty(data.message) ? data.message : messages.join(" ");
  return new AuthApiError(message || (status === 429 ? "Too many attempts. Please try again later."
    : status >= 500 ? "The service is temporarily unavailable. Please try again."
    : status === 401 ? "Incorrect email or password."
    : "The request could not be completed. Please check your details and try again."), status, fields);
}

function loginResponse(value: unknown): LoginResponse {
  if (!record(value) || !nonempty(value.access_token) || String(value.token_type).toLowerCase() !== "bearer"
    || !record(value.user) || !nonempty(value.user.email) || !nonempty(value.user.username)
    || !nonempty(value.user.role) || !["string", "number"].includes(typeof value.user.account_id)
    || !String(value.user.account_id).trim()) throw new AuthApiError("The server returned an invalid sign-in response. Please try again.", 502);
  return { access_token: value.access_token, token_type: "bearer", user: {
    account_id: String(value.user.account_id), email: value.user.email, username: value.user.username, role: value.user.role,
  } };
}

export function createAuthApi({ baseUrl = API_BASE_URL, fetchImpl = fetch, timeoutMs = 15000 }:
  { baseUrl?: string; fetchImpl?: typeof fetch; timeoutMs?: number } = {}) {
  async function request(route: string, body: unknown): Promise<unknown> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetchImpl(baseUrl.replace(/\/+$/, "") + "/auth/" + route, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal: controller.signal,
      });
      const data: unknown = await response.json().catch(() => null);
      if (!response.ok) throw authResponseError(data, response.status);
      return data;
    } catch (error) {
      if (error instanceof AuthApiError) throw error;
      throw new AuthApiError(controller.signal.aborted ? "The request timed out. Please try again."
        : "Cannot connect to the server. Check your connection and try again.", 0);
    } finally { clearTimeout(timeout); }
  }
  return {
    async register(data: RegisterData): Promise<RegisterResponse> {
      const value = await request("register", { ...data, email: data.email.trim().toLowerCase(), username: data.username.trim() });
      if (!record(value) || !["string", "number"].includes(typeof value.account_id) || !String(value.account_id).trim()
        || !nonempty(value.email) || !nonempty(value.username)) throw new AuthApiError("The server returned an invalid registration response. Please try signing in before registering again.", 502);
      return { account_id: String(value.account_id), email: value.email, username: value.username,
        message: nonempty(value.message) ? value.message : "Registration successful." };
    },
    async login(data: LoginData) { return loginResponse(await request("login", { ...data, email: data.email.trim().toLowerCase() })); },
    async google(idToken: string) { return loginResponse(await request("google", { id_token: idToken })); },
    async forgot(email: string) {
      const result = await request("forgot-password", { email: email.trim().toLowerCase() });
      if (!record(result) || !nonempty(result.message)) throw new AuthApiError("The server returned an invalid response. Please try again.", 502);
      return { message: result.message };
    },
    async reset(token: string, password: string) {
      const result = await request("reset-password", { token, new_password: password });
      if (!record(result) || !nonempty(result.message)) throw new AuthApiError("The server returned an invalid response. Please try again.", 502);
      return { message: result.message };
    },
  };
}
