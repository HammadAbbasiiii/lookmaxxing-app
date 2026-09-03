// Token store + global auth events (§5.4, §7.3).
//
// The JWT carries only `sub` (user id) + `exp`. Entitlements are NEVER read
// from localStorage for gating — they come from GET /auth/me (server reads DB).
// The token is stored in localStorage per §5.4 for V1.

const TOKEN_KEY = "lookmaxx_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

// A global "session expired / invalid" signal. The API client fires it on any
// 401; AuthGuard listens and redirects to /login without a flash of broken UI.
export const UNAUTHORIZED_EVENT = "lookmaxx:unauthorized";

export function emitUnauthorized(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  }
}
