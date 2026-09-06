import { test, expect, type Page } from "@playwright/test";
import { ensureUser, setSession, uniqueEmail } from "./helpers";

/** Attach a pageerror collector and return it; assert no uncaught JS errors. */
function collectPageErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  return errors;
}

test.describe("momentum pages load (authed)", () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("pages"));
    await setSession(page, token);
  });

  test("@critical /arc loads without errors", async ({ page }) => {
    const errors = collectPageErrors(page);
    await page.goto("/arc");
    await expect(page.getByText("Today's quests")).toBeVisible();
    await expect(page.getByText("Skill tree")).toBeVisible();
    expect(errors).toEqual([]);
  });

  test("@critical /glow loads without errors", async ({ page }) => {
    const errors = collectPageErrors(page);
    await page.goto("/glow");
    await expect(
      page.getByRole("heading", { name: "Daily Glow" }),
    ).toBeVisible();
    expect(errors).toEqual([]);
  });

  test("@critical /glowups loads without errors", async ({ page }) => {
    const errors = collectPageErrors(page);
    await page.goto("/glowups");
    await expect(page.getByText("Real transformations")).toBeVisible();
    expect(errors).toEqual([]);
  });

  test("@critical /dashboard loads without errors", async ({ page }) => {
    const errors = collectPageErrors(page);
    await page.goto("/dashboard");
    await expect(page.getByRole("main")).toBeVisible();
    expect(errors).toEqual([]);
  });
});
