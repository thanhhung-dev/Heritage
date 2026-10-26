export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const FALLBACK_API_BASE_URL = "http://localhost:8000/api";

export async function apiClient<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const normalizedEndpoint = endpoint.startsWith("/")
    ? endpoint
    : `/${endpoint}`;
  const primaryUrl = `${API_BASE_URL}${normalizedEndpoint}`;

  let response: Response;
  try {
    response = await fetch(primaryUrl, {
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
      ...options,
    });
  } catch (err) {
    if (API_BASE_URL !== FALLBACK_API_BASE_URL) {
      response = await fetch(`${FALLBACK_API_BASE_URL}${normalizedEndpoint}`, {
        headers: {
          "Content-Type": "application/json",
          ...options?.headers,
        },
        ...options,
      });
    } else {
      throw err;
    }
  }

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText} (${response.status})`);
  }

  return response.json();
}
