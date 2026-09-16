import { test, expect } from "@playwright/test";
import { ensureUser, setSession, uniqueEmail } from "./helpers";

/**
 * Tier clarity (DEF-011 / DEF-012).
 *
 * `ensureUser` always creates a *free* member, so this spec pins the free-tier
 * view — the one that has to sell the paid tiers. Two rules are asserted:
 *   1. a gated destination says Pro/Elite **before** the tap (nav hints), and
 *   2. a locked surface links to the plan that actually unlocks it — and names
 *      the right plan, so "Upgrade to Pro" never fronts an Elite-only feature.
 * The backend is the real gate; this only guards the labelling.
 */
test.describe("tier clarity for a free member", () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("tier"));
    await setSession(page, token);
  });

  test("@critical desktop nav marks Coach as Pro and leaves free tabs alone", async ({
    page,
  }) => {
    await page.goto("/dashboard");
    const nav = page.locator('nav[aria-label="Primary"]');
    // The padlock's sr-only text is what carries the tier to the a11y tree.
    await expect(nav.locator('a[href="/coach"]')).toContainText("Pro");
    for (const href of ["/dashboard", "/plan", "/glow", "/explore"]) {
      await expect(nav.locator(`a[href="${href}"]`)).not.toContainText("Pro");
    }
  });

  test("@critical mobile tab bar repeats the Coach hint", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/dashboard");
    const tabBar = page.locator('nav[aria-label="Bottom"]');
    await expect(tabBar.locator('a[href="/coach"]')).toContainText("Pro");
    await expect(tabBar.locator('a[href="/plan"]')).not.toContainText("Pro");
  });

  test("@critical Glow sub-nav marks Insights and Simulator as Pro", async ({ page }) => {
    await page.goto("/glow");
    const subNav = page.locator('nav[aria-label="Glow"]');
    await expect(subNav.locator('a[href="/glow-up"]')).toContainText("Pro");
    await expect(subNav.locator('a[href="/peak-you"]')).toContainText("Pro");
    // Daily is free and Journey is free-but-quests — neither gets a hint.
    await expect(subNav.locator('a[href="/glow"]')).not.toContainText("Pro");
    await expect(subNav.locator('a[href="/arc"]')).not.toContainText("Pro");
  });

  test("every locked surface links to the plan that unlocks it", async ({ page }) => {
    const cases: { path: string; cta: string; needsAnalysis?: boolean }[] = [
      { path: "/coach", cta: "Upgrade to Pro" },
      // /glow-up and /peak-you render their Pro lock only *after* an analysis
      // exists — without one the same route is the "No analysis yet" empty state
      // (true for any real user before their first photo, and for this suite,
      // which creates users through the API where no local MediaPipe model is
      // available). The locked state of both routes is asserted deterministically
      // in score-clarity.spec.ts with a stubbed analysis payload.
      { path: "/glow-up", cta: "Upgrade to Pro", needsAnalysis: true },
      { path: "/peak-you", cta: "Upgrade to Pro", needsAnalysis: true },
      { path: "/arc", cta: "Upgrade to Pro" },
      { path: "/glowups", cta: "Upgrade to Elite" },
    ];
    for (const { path, cta, needsAnalysis } of cases) {
      await page.goto(path);
      if (needsAnalysis) {
        // Either state is correct for a user the suite created through the API:
        // the Pro lock (when an analysis exists) or the pre-analysis empty state.
        // `score-clarity.spec.ts` asserts the lock itself deterministically.
        await expect(
          page.getByText(cta).or(page.getByText("No analysis yet")),
        ).toBeVisible();
        continue;
      }
      await expect(page.getByText(cta).first()).toBeVisible();
    }
  });

  test("dashboard separates Pro perks from Elite perks", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.getByText("Pro unlocks")).toBeVisible();
    await expect(page.getByText("Elite only")).toBeVisible();
    await expect(page.getByRole("link", { name: /See Pro & Elite/i })).toBeVisible();
  });
});
