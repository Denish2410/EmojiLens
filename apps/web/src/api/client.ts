import type { ApiErrorBody, Health, Readiness, UnicodeAnalysis } from "./types";

export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function isErrorBody(x: unknown): x is ApiErrorBody {
  return (
    typeof x === "object" &&
    x !== null &&
    "error" in x &&
    typeof (x as ApiErrorBody).error?.code === "string"
  );
}

async function request<T>(path: string, init?: RequestInit, allow?: number[]): Promise<T> {
  let res: Response;
  try {
    res = await fetch(new URL(`${API_BASE}${path}`, window.location.origin), {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, "network_error", "Could not reach the EmojiLens API.");
  }
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok && !allow?.includes(res.status)) {
    if (isErrorBody(body)) {
      throw new ApiError(res.status, body.error.code, body.error.message, body.error.details);
    }
    throw new ApiError(res.status, "http_error", `Request failed with status ${res.status}.`);
  }
  return body as T;
}

export const api = {
  health: () => request<Health>("/health"),
  ready: () => request<Readiness>("/ready", undefined, [503]),
  analyzeUnicode: (text: string) =>
    request<UnicodeAnalysis>("/unicode/analyze", {
      method: "POST",
      // JSON.stringify preserves every code point; lone surrogates are escaped as \uD8xx
      // and rejected server-side with invalid_unicode.
      body: JSON.stringify({ text }),
    }),
};
