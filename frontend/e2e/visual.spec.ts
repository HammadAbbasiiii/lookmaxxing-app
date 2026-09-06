import { test } from "@playwright/test";
import { ensureUser, setSession, uniqueEmail } from "./helpers";

/**
 * Visual evidence capture. Saves full-page screenshots of the key surfaces to
 * TESTING/screenshots/ for manual review. Automated visual *regression* (baseline
 * diffing via toHaveScreenshot) is intentionally not wired into CI this pass to
 * avoid environment-specific font-rendering flakes; see TESTING/TEST-RESULTS.md.
 */
const OUT = "../TESTING/screenshots";

test("capture: landing", async ({ page }) => {
  await page.goto("/");
  await page.screenshot({ path: `${OUT}/landing.png`, fullPage: true });
});

test("capture: login", async ({ page }) => {
  await page.goto("/login");
  await page.screenshot({ path: `${OUT}/login.png`, fullPage: true });
});

test("capture: signup", async ({ page }) => {
  await page.goto("/signup");
  await page.screenshot({ path: `${OUT}/signup.png`, fullPage: true });
});

test("capture: dashboard / arc / glow / glowups (authed)", async ({
  page,
  request,
}) => {
  const token = await ensureUser(request, uniqueEmail("shot"));
  await setSession(page, token);

  for (const route of ["/dashboard", "/arc", "/glow", "/glowups"]) {
    await page.goto(route);
    await page.waitForLoadState("networkidle").catch(() => {});
    await page.screenshot({
      path: `${OUT}/${route.slice(1) || "index"}.png`,
      fullPage: true,
    });
  }
});
