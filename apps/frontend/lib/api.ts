import { API_BASE_URL } from "../config/api";

export interface ApiDependencies {
  fetchImpl?: typeof fetch;
  randomUUID?: () => string;
  accessToken?: string | null;
  signal?: AbortSignal;
}

/**
 * Standard API error with HTTP status code.
 */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/**
 * Build a clean API URL without duplicating `/api` prefix.
 * Supports both single-argument `buildApiUrl("/chat")` using default API_BASE_URL,
 * and 2-argument `chatApiUrl(apiUrl, "/chat")` for testing / custom base URLs.
 */
export function buildApiUrl(baseUrlOrRoute: string, route?: string): string {
  if (route === undefined) {
    const routeOnly = baseUrlOrRoute;
    const base = API_BASE_URL.replace(/\/+$/, "");
    const apiRoot = /\/api$/i.test(base) ? base : `${base}/api`;
    const normalizedRoute = routeOnly.startsWith("/") ? routeOnly : `/${routeOnly}`;
    return `${apiRoot}${normalizedRoute}`;
  }

  let base: string;
  let targetRoute: string;

  if (/^https?:\/\//i.test(baseUrlOrRoute)) {
    base = baseUrlOrRoute.replace(/\/+$/, "");
    targetRoute = route;
  } else if (/^https?:\/\//i.test(route)) {
    base = route.replace(/\/+$/, "");
    targetRoute = baseUrlOrRoute;
  } else {
    base = baseUrlOrRoute.replace(/\/+$/, "");
    targetRoute = route;
  }

  const apiRoot = /\/api$/i.test(base) ? base : `${base}/api`;
  const normalizedRoute = targetRoute.startsWith("/") ? targetRoute : `/${targetRoute}`;
  return `${apiRoot}${normalizedRoute}`;
}

/**
 * Alias for backward compatibility.
 */
export const chatApiUrl = buildApiUrl;

/**
 * Common fetch wrapper that automatically attaches Correlation ID,
 * JSON headers, Bearer auth token, and signal handling.
 */
export function apiFetch(
  route: string,
  options: RequestInit = {},
  deps: ApiDependencies = {},
  baseUrl?: string,
): Promise<Response> {
  const fetchImpl = deps.fetchImpl ?? fetch;
  const randomUUID = deps.randomUUID ?? (() => crypto.randomUUID());
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Correlation-ID": randomUUID(),
    ...((options.headers as Record<string, string>) || {}),
  };

  if (deps.accessToken) {
    headers.Authorization = `Bearer ${deps.accessToken}`;
  }

  const url = buildApiUrl(route, baseUrl);
  return fetchImpl(url, {
    ...options,
    headers,
    signal: deps.signal ?? options.signal,
  });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/**
 * Parse JSON safely and throw localized ApiError with descriptive message.
 */
export async function parseApiResponse<T>(response: Response): Promise<T> {
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = isRecord(data) ? data.detail : null;
    const text =
      typeof detail === "string"
        ? detail
        : isRecord(detail) && typeof detail.message === "string"
          ? detail.message
          : null;
    const message =
      response.status === 401
        ? "Phiên đăng nhập đã hết hạn hoặc không hợp lệ. Vui lòng đăng nhập lại."
        : text ?? `Yêu cầu thất bại (${response.statusText || response.status}). Vui lòng thử lại.`;
    throw new ApiError(message, response.status);
  }
  return data as T;
}
