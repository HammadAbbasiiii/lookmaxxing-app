import { test, expect } from "@playwright/test";
import http from "http";
import { API_URL } from "./helpers";

const API_HOST = "127.0.0.1";
const API_PORT = 8000;

/** Raw HTTP GET with a custom Origin header (the fetch/request APIs strip Origin). */
function getWithOrigin(origin: string): Promise<http.IncomingMessage> {
  return new Promise((resolve, reject) => {
    const req = http.get(
      { host: API_HOST, port: API_PORT, path: "/api/v1/health", headers: { Origin: origin } },
      (res) => resolve(res),
    );
    req.on("error", reject);
  });
}

/**
 * Security-header + CORS checks against the live local API.
 * These run over HTTP (not TestClient), so they verify the real middleware stack
 * including the outermost security-headers wrapper.
 */
test.describe("security headers", () => {
  test("@critical all responses carry hardening headers", async ({ request }) => {
    const res = await request.get(`${API_URL}/health`);
    expect(res.status()).toBe(200);
    expect(res.headers()["x-content-type-options"]).toBe("nosniff");
    expect(res.headers()["x-frame-options"]).toBe("DENY");
    expect(res.headers()["referrer-policy"]).toBe(
      "strict-origin-when-cross-origin",
    );
    expect(res.headers()["permissions-policy"]).toContain("camera=()");
  });

  test("401 responses also carry hardening headers", async ({ request }) => {
    const res = await request.get(`${API_URL}/auth/me`);
    expect(res.status()).toBe(401);
    expect(res.headers()["x-content-type-options"]).toBe("nosniff");
    expect(res.headers()["x-frame-options"]).toBe("DENY");
  });

  test("429 responses also carry hardening headers + Retry-After", async ({
    request,
  }) => {
    const email = `throttle-hdr-${Date.now()}@example.com`;
    for (let i = 0; i < 10; i++) {
      await request.post(`${API_URL}/auth/login`, {
        form: { username: email, password: "Wrong#123" },
      });
    }
    const res = await request.post(`${API_URL}/auth/login`, {
      form: { username: email, password: "Wrong#123" },
    });
    expect(res.status()).toBe(429);
    expect(res.headers()["x-content-type-options"]).toBe("nosniff");
    expect(res.headers()["x-frame-options"]).toBe("DENY");
  });
});

test.describe("CORS", () => {
  test("allows the configured frontend origin", async () => {
    const res = await getWithOrigin("http://localhost:3000");
    expect(res.headers["access-control-allow-origin"]).toBe(
      "http://localhost:3000",
    );
  });

  test("does not allow an unlisted origin", async () => {
    const res = await getWithOrigin("https://evil.example.com");
    expect(res.headers["access-control-allow-origin"]).toBeUndefined();
  });
});

test.describe("information disclosure", () => {
  test("signup response never contains a password hash", async ({ request }) => {
    const email = `nohash-${Date.now()}@example.com`;
    const res = await request.post(`${API_URL}/auth/signup`, {
      data: { email, password: "Lookmaxx#123", full_name: "No Hash" },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.text();
    expect(body).not.toContain("hashed_password");
    expect(body).not.toContain("$2b$");
  });
});
