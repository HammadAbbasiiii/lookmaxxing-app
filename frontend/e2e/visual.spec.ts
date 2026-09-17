import { test, type Page } from "@playwright/test";
import { ensureUser, setSession, uniqueEmail } from "./helpers";

/**
 * Visual evidence capture. Saves full-page screenshots of the key surfaces to
 * TESTING/screenshots/ for manual review. Automated visual *regression* (baseline
 * diffing via toHaveScreenshot) is intentionally not wired into CI this pass to
 * avoid environment-specific font-rendering flakes; see TESTING/TESTING-RESULTS.md.
 */
const OUT = "../TESTING/screenshots";

/**
 * Fire every scroll-triggered reveal before capturing.
 *
 * A full-page screenshot resizes the viewport and snaps immediately, so it races
 * the IntersectionObserver behind `Reveal` and records every below-the-fold block
 * at `opacity: 0`. The 2026-09-17 adversarial pass measured 35 invisible landing
 * text blocks in exactly that way — the page is fine for a human who scrolls, but
 * the evidence was lying. Scroll through, come back, then capture.
 */
async function settleReveals(page: Page): Promise<void> {
  await page.evaluate(async () => {
    const step = window.innerHeight * 0.8;
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo({ top: y, behavior: "instant" });
      await new Promise((resolve) => requestAnimationFrame(() => setTimeout(resolve, 60)));
    }
    window.scrollTo({ top: 0, behavior: "instant" });
  });
  // The longest reveal is 0.6s, plus any delay prop.
  await page.waitForTimeout(900);
}

test("capture: landing", async ({ page }) => {
  await page.goto("/");
  await settleReveals(page);
  await page.screenshot({ path: `${OUT}/landing.png`, fullPage: true });
});

test("capture: login", async ({ page }) => {
  await page.goto("/login");
  await settleReveals(page);
  await page.screenshot({ path: `${OUT}/login.png`, fullPage: true });
});

test("capture: signup", async ({ page }) => {
  await page.goto("/signup");
  await settleReveals(page);
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
    await settleReveals(page);
    await page.screenshot({
      path: `${OUT}/${route.slice(1) || "index"}.png`,
      fullPage: true,
    });
  }
});
