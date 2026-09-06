import { test, expect } from "@playwright/test";
import { setSession } from "./helpers";

test.describe("route guard / 401 handling", () => {
  test("anonymous user is redirected from a protected route", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login\?next=/);
  });

  test("an invalid token is cleared and the user bounced to login", async ({
    page,
  }) => {
    await setSession(page, "not-a-real-jwt");
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
    const token = await page.evaluate(() =>
      window.localStorage.getItem("lookmaxx_token"),
    );
    expect(token).toBeNull();
  });

  test("invalid route renders the 404 page", async ({ page }) => {
    await page.goto("/this-route-does-not-exist");
    await expect(page.getByText(/not found|doesn't exist|404/i).first()).toBeVisible();
  });
});
