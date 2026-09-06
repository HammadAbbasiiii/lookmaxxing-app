import type { APIRequestContext, Page } from "@playwright/test";

// Local backend used by the E2E suite (see playwright.config.ts webServer).
export const API_URL = "http://127.0.0.1:8000/api/v1";
export const TOKEN_KEY = "lookmaxx_token";
// Strong (4 classes), not in the common blocklist.
export const TEST_PASSWORD = "Lookmaxx#123";

let counter = 0;

export function uniqueEmail(prefix = "e2e"): string {
  counter += 1;
  return `${prefix}-${Date.now()}-${counter}@example.com`;
}

export async function signupViaApi(
  request: APIRequestContext,
  email: string,
  password: string = TEST_PASSWORD,
) {
  return request.post(`${API_URL}/auth/signup`, {
    data: { email, password, full_name: "E2E User" },
  });
}

export async function loginViaApi(
  request: APIRequestContext,
  email: string,
  password: string = TEST_PASSWORD,
): Promise<string> {
  const res = await request.post(`${API_URL}/auth/login`, {
    form: { username: email, password },
  });
  const body = (await res.json()) as { access_token?: string };
  if (!body.access_token) {
    throw new Error(`login failed for ${email}: HTTP ${res.status()}`);
  }
  return body.access_token;
}

/** Idempotent: sign up (ignoring "already exists") then log in; returns token. */
export async function ensureUser(
  request: APIRequestContext,
  email: string,
  password: string = TEST_PASSWORD,
): Promise<string> {
  await signupViaApi(request, email, password);
  return loginViaApi(request, email, password);
}

/**
 * Pre-seed localStorage with a token on every navigation, so authed pages render
 * without driving the UI login form each time.
 */
export async function setSession(page: Page, token: string): Promise<void> {
  await page.addInitScript((value: string) => {
    window.localStorage.setItem("lookmaxx_token", value);
  }, token);
}
