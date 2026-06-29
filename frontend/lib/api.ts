export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

export function apiHeaders(extra: Record<string, string> = {}): HeadersInit {
  const headers: Record<string, string> = { ...extra };
  if (API_KEY) headers["X-API-Key"] = API_KEY;
  return headers;
}
