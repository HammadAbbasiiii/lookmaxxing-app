import { test, expect, type Page } from "@playwright/test";
import { ensureUser, setSession, uniqueEmail } from "./helpers";

/**
 * Mobile account drawer (DEF-010).
 *
 * The drawer used to be rendered *inside* the sticky `<header>`. `backdrop-blur`
 * on the header is a `backdrop-filter`, which makes that element the containing
 * block for `position: fixed` descendants — so the drawer's `fixed inset-0`
 * overlay resolved against the 64px header box, its `overflow-hidden` clipped
 * every menu row, and the header (`z-40`) formed a stacking context that trapped
 * the overlay *beneath* the bottom tab bar. Net effect: on any phone viewport
 * the account menu opened as a 64px sliver and Profile / Settings / Upgrade /
 * Log out could not be tapped.
 *
 * The drawer must stay a sibling of `<header>`: moving it back inside makes the
 * geometry and click assertions below fail again.
 */
const MOBILE = { width: 390, height: 844 };

/** Desktop + mobile avatars share this label; only one is ever on screen. */
const avatar = (page: Page) => page.locator('button[aria-label="Account menu"]:visible');
const drawer = (page: Page) => page.getByRole("dialog", { name: "Account menu" });

/**
 * Whether a drawer row actually receives a tap at its own centre. Playwright's
 * click actionability alone is not enough here: a row clipped away by an
 * ancestor's `overflow-hidden` still reports a non-empty bounding box.
 */
async function rowReceivesTap(page: Page, label: string): Promise<boolean> {
  return page.evaluate((wanted) => {
    const row = [...document.querySelectorAll('aside[role="dialog"] button')].find(
      (b) => b.textContent?.trim() === wanted,
    );
    if (!row) return false;
    const box = row.getBoundingClientRect();
    if (!box.height) return false;
    const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
    return Boolean(hit && (hit === row || row.contains(hit)));
  }, label);
}

test.describe("mobile account drawer", () => {
  test.use({ viewport: MOBILE });

  test.beforeEach(async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("drawer"));
    await setSession(page, token);
    await page.goto("/dashboard");
  });

  test("@critical opens unclipped with every account action", async ({ page }) => {
    await avatar(page).click();
    await expect(drawer(page)).toBeVisible();

    const geometry = await page.evaluate(() => {
      const dialog = document.querySelector('aside[role="dialog"]');
      if (!dialog) return null;
      return {
        overlayHeight: Math.round(dialog.parentElement!.getBoundingClientRect().height),
        viewportHeight: window.innerHeight,
        insideHeader: Boolean(dialog.closest("header")),
      };
    });

    // A blurred ancestor re-clips the overlay to the header box (DEF-010).
    expect(geometry?.insideHeader).toBe(false);
    expect(geometry!.overlayHeight).toBeGreaterThan(geometry!.viewportHeight * 0.9);

    for (const name of ["Profile", "Settings", "Upgrade", "Log out"]) {
      await expect(drawer(page).getByRole("button", { name })).toBeVisible();
      // expect.poll waits out the 200ms slide-in before hit-testing.
      await expect.poll(() => rowReceivesTap(page, name)).toBe(true);
    }
  });

  test("@critical tapping Profile opens settings", async ({ page }) => {
    await avatar(page).click();
    await expect.poll(() => rowReceivesTap(page, "Profile")).toBe(true);
    // Clicks run Playwright's hit-target check, so a clipped row fails here.
    await drawer(page).getByRole("button", { name: "Profile" }).click();

    await expect(page).toHaveURL(/\/settings$/);
    await expect(drawer(page)).toBeHidden();
  });

  test("Upgrade sends a free member to /upgrade", async ({ page }) => {
    await avatar(page).click();
    await expect.poll(() => rowReceivesTap(page, "Upgrade")).toBe(true);
    await drawer(page).getByRole("button", { name: "Upgrade" }).click();

    await expect(page).toHaveURL(/\/upgrade$/);
  });

  test("Escape closes the drawer and restores page scroll", async ({ page }) => {
    await avatar(page).click();
    await expect(drawer(page)).toBeVisible();
    expect(await page.evaluate(() => document.body.style.overflow)).toBe("hidden");

    await page.keyboard.press("Escape");

    await expect(drawer(page)).toBeHidden();
    expect(await page.evaluate(() => document.body.style.overflow)).toBe("");
  });

  test("open drawer covers the bottom tab bar and closes on a backdrop tap", async ({
    page,
  }) => {
    await avatar(page).click();
    await expect(drawer(page)).toBeVisible();

    const tabBar = page.locator('nav[aria-label="Bottom"]');
    const box = (await tabBar.boundingBox())!;
    const center = { x: box.x + box.width / 2, y: box.y + box.height / 2 };

    // The tab bar is behind the drawer, so a tap lands on the backdrop…
    const hitsTabBar = await page.evaluate(
      ({ x, y }) =>
        Boolean(
          document.elementFromPoint(x, y)?.closest('nav[aria-label="Bottom"]'),
        ),
      center,
    );
    expect(hitsTabBar).toBe(false);

    // …and that backdrop tap dismisses the drawer.
    await page.mouse.click(center.x, center.y);
    await expect(drawer(page)).toBeHidden();
  });
});
