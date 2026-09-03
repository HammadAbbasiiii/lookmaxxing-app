// Typed, never-crash HTTP client (§7.3 #3, §9.4, §9.5).
//
// Responsibilities:
//  1. Attach the bearer token.
//  2. Parse JSON defensively (non-JSON → treated as a 500).
//  3. Normalize FastAPI `{detail}` (string OR array) into a readable message.
//  4. Map network/timeout to a distinct first-class error.
//  5. Fire the global 401 handler (clear token + redirect).
//  6. Truncate/log without ever leaking secrets.

import { API_BASE } from "@/lib/constants";
import { clearToken, emitUnauthorized, getToken } from "@/lib/auth";
import { truncate } from "@/lib/utils";

export type ApiErrorCode = "network" | "timeout" | "http" | "parse";

export class ApiError extends Error {
  status: number;
  code: ApiErrorCode;

  constructor(status: number, code: ApiErrorCode, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export interface FetchOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  /** JSON body (default) — object will be stringified. */
  body?: unknown;
  /** Send `body` as application/x-www-form-urlencoded (OAuth2 login, /upload/save). */
  form?: boolean;
  /** `body` is already a FormData instance (multipart). */
  isFormData?: boolean;
  headers?: Record<string, string>;
  timeoutMs?: number;
}

/** FastAPI returns `detail` as either a string or a 422 array of {loc,msg}. */
function normalizeDetail(data: unknown): string {
  if (!data || typeof data !== "object") return "";
  const record = data as Record<string, unknown>;

  const detail = record.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in (item as object)) {
          return String((item as { msg: unknown }).msg ?? "");
        }
        return "";
      })
      .filter(Boolean)
      .join(" ");
  }

  if (typeof record.message === "string") return record.message;
  return "";
}

function httpErrorMessage(status: number, data: unknown): string {
  const detail = normalizeDetail(data);
  if (detail) return truncate(detail);

  // §9.4 status → copy map.
  switch (status) {
    case 400:
      return "Something's not right with that request. Check and try again.";
    case 403:
      return "Upgrade to Pro to unlock this.";
    case 404:
      return "Not found.";
    case 413:
      return "That photo is too big. Max 10MB.";
    case 422:
      return "Enter valid information and try again.";
    case 429:
      return "Too many requests. Wait a moment.";
    case 500:
      return "Something went wrong on our end. Please try again.";
    default:
      return "Something went wrong. Please try again.";
  }
}

export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const {
    method = "GET",
    body,
    form = false,
    isFormData = false,
    headers = {},
    timeoutMs = 10_000,
  } = options;

  const url = `${API_BASE}${path}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const finalHeaders: Record<string, string> = { Accept: "application/json", ...headers };
  const token = getToken();
  if (token) finalHeaders.Authorization = `Bearer ${token}`;

  let payload: BodyInit | undefined;
  if (body !== undefined && body !== null) {
    if (isFormData) {
      payload = body as FormData;
    } else if (form) {
      finalHeaders["Content-Type"] = "application/x-www-form-urlencoded";
      payload = new URLSearchParams(body as Record<string, string>).toString();
    } else {
      finalHeaders["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: finalHeaders,
      body: payload,
      signal: controller.signal,
    });
  } catch (error) {
    clearTimeout(timer);
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(0, "timeout", "Can't reach the server. Check your connection and try again.");
    }
    throw new ApiError(0, "network", "Can't reach the server. Check your connection and try again.");
  }
  clearTimeout(timer);

  // Session invalid → clear + global redirect (§9.1 #3).
  if (response.status === 401) {
    clearToken();
    emitUnauthorized();
    throw new ApiError(401, "http", "Incorrect email or password.");
  }

  // Defensive parse: a proxy/HTML error page is treated as a 500 (§9.5).
  const text = await response.text().catch(() => "");
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!response.ok) {
    const message = data === null
      ? httpErrorMessage(response.status, null)
      : httpErrorMessage(response.status, data);
    // Log raw detail (truncated) for debugging — never shown to the user.
    if (typeof window !== "undefined") {
      console.warn(`[api] ${response.status} ${method} ${path}: ${truncate(text, 300)}`);
    }
    throw new ApiError(response.status, "http", message);
  }

  if (data === null) return {} as T;
  return data as T;
}

/** Upload helper with a longer timeout (20s per §9.1 #8) — never hangs. */
export async function apiFetchUpload<T>(path: string, options: FetchOptions = {}): Promise<T> {
  return apiFetch<T>(path, { ...options, timeoutMs: 20_000 });
}
