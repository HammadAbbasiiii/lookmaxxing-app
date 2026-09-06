import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { ensureUser, setSession, uniqueEmail } from "./helpers";

/**
 * Automated accessibility scans (axe-core). This is NOT a WCAG conformance
 * claim — it catches structural issues (labels, roles, landmarks, contrast,
 * duplicate IDs). Critical + serious violations are hard failures.
 */
test.describe("accessibility", () => {
  test("@critical login has no critical/serious violations", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("heading", { name: "Welcome back" }).waitFor();
    const results = await new AxeBuilder({ page }).analyze();
    const blocked = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(blocked).toEqual([]);
  });

  test("@critical signup has no critical/serious violations", async ({
    page,
  }) => {
    await page.goto("/signup");
    await page
      .getByRole("heading", { name: "Create your account" })
      .waitFor();
    const results = await new AxeBuilder({ page }).analyze();
    const blocked = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(blocked).toEqual([]);
  });

  test("dashboard has no critical/serious violations", async ({
    page,
    request,
  }) => {
    const token = await ensureUser(request, uniqueEmail("a11y"));
    await setSession(page, token);
    await page.goto("/dashboard");
    await page.getByRole("main").waitFor();
    const results = await new AxeBuilder({ page }).analyze();
    const blocked = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(blocked).toEqual([]);
  });

  test("password toggle is keyboard operable", async ({ page }) => {
    await page.goto("/signup");
    const toggle = page.getByRole("button", { name: "Show password" });
    await expect(toggle).toBeVisible();

    // It must be reachable and activatable via keyboard (Enter/Space).
    await toggle.focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("button", { name: "Hide password" }),
    ).toBeVisible();
    // The input's type should flip to text so the value is visible.
    const type = await page.locator("#password").getAttribute("type");
    expect(type).toBe("text");
  });
});
