const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

interface CsrfResponse {
  csrfToken: string;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function getCsrfToken(): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/auth/csrf/`, {
    credentials: "include",
    cache: "no-store",
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new ApiError(response.statusText, response.status);
  }

  const body = (await response.json()) as CsrfResponse;
  return body.csrfToken;
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  headers.set("Accept", "application/json");
  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
    headers.set("X-CSRFToken", await getCsrfToken());
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    method,
    credentials: "include",
    headers,
  });

  if (!response.ok) {
    let message = response.statusText;
    try {
      const body = (await response.json()) as {
        detail?: string;
        message?: string;
      };
      message = body.detail ?? body.message ?? message;
    } catch {
      // Keep the HTTP status when the server does not return JSON.
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
