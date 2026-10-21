import { requestMockApi } from "@/mocks";
import type { components } from "@/types/api.generated";

export const API_BASE_URL =
  (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export type ApiErrorBody =
  | components["schemas"]["ChatErrorResponse"]
  | components["schemas"]["HTTPValidationError"];

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: ApiErrorBody,
  ) {
    const detail = body.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg).join("; ")
          : detail
            ? JSON.stringify(detail)
            : `API error (${status})`;
    super(message);
    this.name = "ApiError";
  }
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  return (
    typeof value === "object" &&
    value !== null &&
    "detail" in value &&
    (typeof value.detail === "string" ||
      (typeof value.detail === "object" && value.detail !== null))
  );
}

export async function apiClient<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const headers = new Headers(options?.headers);
  if (typeof options?.body === "string" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const requestOptions: RequestInit = {
    ...options,
    headers,
  };

  const response =
    API_BASE_URL === "mock"
      ? await requestMockApi(endpoint, requestOptions)
      : await fetch(
          `${API_BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`,
          requestOptions,
        );

  if (!response.ok) {
    const payload: unknown = await response.json().catch(() => null);
    const body = isApiErrorBody(payload)
      ? payload
      : { detail: response.statusText || `API error (${response.status})` };
    throw new ApiError(response.status, body);
  }

  return response.json();
}
