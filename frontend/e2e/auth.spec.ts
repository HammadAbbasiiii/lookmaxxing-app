import { test, expect } from "@playwright/test";
import {
  API_URL,
  TEST_PASSWORD,
  ensureUser,
  uniqueEmail,
} from "./helpers";

test.describe("signup", () => {
  test("@critical weak password is rejected with a strength-meter verdict", async ({
    page,
  }) => {
    await page.goto("/signup");

    await page.fill("#password", "password123");
    // Live strength meter (a div[aria-live] region — the toast region also uses
    // aria-live, so scope to the meter div specifically).
    await expect(page.locator("div[aria-live='polite']")).toContainText(
      "Too common",
    );

    await page.fill("#email", "weak-password@example.com");
    await page.getByLabel(/I agree to the/).check();
    await page.getByRole("button", { name: "Create account" }).click();

    // Client-side rejection mirrors the backend; no account is created.
    await expect(
      page.getByText("That password is too common. Choose something more unique."),
    ).toBeVisible();
  });

  test("valid signup creates an account and lands on onboarding", async ({
    page,
  }) => {
    const email = uniqueEmail("signup");
    await page.goto("/signup");
    await page.fill("#email", email);
    await page.fill("#full_name", "E2E User");
    await page.fill("#password", TEST_PASSWORD);
    await page.getByLabel(/I agree to the/).check();
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page).toHaveURL(/onboarding/, { timeout: 20_000 });
  });

  test("duplicate email shows the already-registered message", async ({
    page,
    request,
  }) => {
    const email = uniqueEmail("dup");
    await ensureUser(request, email);

    await page.goto("/signup");
    await page.fill("#email", email);
    await page.fill("#password", TEST_PASSWORD);
    await page.getByLabel(/I agree to the/).check();
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(
      page.getByText("That email is already registered. Log in instead."),
    ).toBeVisible();
  });
});

test.describe("login", () => {
  test("@critical wrong password shows anti-enumeration copy", async ({
    page,
    request,
  }) => {
    const email = uniqueEmail("login");
    await ensureUser(request, email);

    await page.goto("/login");
    await page.fill("#email", email);
    await page.fill("#password", "WrongPass#99");
    await page.getByRole("button", { name: "Log in" }).click();

    await expect(page.getByText("Incorrect email or password.")).toBeVisible();
  });

  test("valid login stores the token and enters the app", async ({
    page,
    request,
  }) => {
    const email = uniqueEmail("login-ok");
    await ensureUser(request, email);

    await page.goto("/login");
    await page.fill("#email", email);
    await page.fill("#password", TEST_PASSWORD);
    await page.getByRole("button", { name: "Log in" }).click();

    await expect(page).toHaveURL(/dashboard/, { timeout: 20_000 });
    const token = await page.evaluate(() =>
      window.localStorage.getItem("lookmaxx_token"),
    );
    expect(token).toBeTruthy();
  });

  test("login throttle returns 429 after 10 failed attempts", async ({
    request,
  }) => {
    const email = uniqueEmail("throttle");
    for (let i = 0; i < 10; i++) {
      const res = await request.post(`${API_URL}/auth/login`, {
        form: { username: email, password: "Wrong#123" },
      });
      expect(res.status()).toBe(401);
    }
    const blocked = await request.post(`${API_URL}/auth/login`, {
      form: { username: email, password: "Wrong#123" },
    });
    expect(blocked.status()).toBe(429);
    const body = (await blocked.json()) as { detail?: string };
    expect(body.detail).toContain("Too many failed attempts");
  });
});
