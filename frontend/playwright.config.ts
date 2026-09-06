import { defineConfig, devices } from "@playwright/test";

/**
 * LookMaxx E2E config.
 *
 * Two local servers are expected (or auto-started via webServer):
 *  - backend  : FastAPI on http://127.0.0.1:8000 (SQLite e2e.db)
 *  - frontend : Next.js dev on http://localhost:3000 (pointed at the local API)
 *
 * Run the whole suite on Chromium:   npx playwright test --project=chromium
 * Run cross-browser critical set:    npx playwright test --grep "@critical"
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
  webServer: [
    {
      command:
        "DATABASE_URL=sqlite:///./e2e.db RATE_LIMIT_ANONYMOUS=1000 .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      cwd: "../backend",
      url: "http://127.0.0.1:8000/api/v1/health",
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/api/v1 npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: true,
      timeout: 180_000,
    },
  ],
});
