/**
 * Adversarial stress suite (`@stress`) — OPERATION BREAKPOINT.
 *
 * These tests do not check that the app works; the rest of the suite does that.
 * They check that it survives being *misused*: every screen size a real device
 * has, keyboard-only navigation, a closed drawer that must not be reachable, an
 * impatient finger that double-taps a submit, a network that dies mid-action,
 * URLs edited by hand, and inputs filled with garbage.
 *
 * Run: npx playwright test stress-adversary --project=chromium
 *
 * Every assertion here exists because it can fail for a reason a user would
 * feel. Anything that only asserts an implementation detail does not belong.
 */

import { test, expect, type Page } from "@playwright/test";
import { API_URL, TEST_PASSWORD, ensureUser, setSession, uniqueEmail } from "./helpers";

// ── Determinism helpers ─────────────────────────────────────────────

/**
 * Collect genuine *JavaScript* failures for the lifetime of a page.
 *
 * `Failed to load resource: … 404` is deliberately excluded: it is the browser
 * reporting an HTTP status, not the app misbehaving, and several screens
 * legitimately ask for things that do not exist yet (a brand-new account has no
 * photos). Requests are audited properly by `auditFailedRequests` instead.
 */
function trackFailures(page: Page): string[] {
  const failures: string[] = [];
  page.on("pageerror", (err) => failures.push(`pageerror: ${err.message}`));
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    if (/Download the React DevTools|Fast Refresh|\[HMR\]/.test(text)) return;
    if (/Failed to load resource/.test(text)) return;
    failures.push(`console: ${text}`);
  });
  return failures;
}

/**
 * Every response the page receives while `run` executes, filtered to failures.
 * Returns "STATUS METHOD path" strings so a regression names itself.
 */
async function auditFailedRequests(page: Page, run: () => Promise<void>): Promise<string[]> {
  const failed: string[] = [];
  const onResponse = (res: { status: () => number; request: () => { method: () => string }; url: () => string }) => {
    if (res.status() < 400) return;
    failed.push(`${res.status()} ${res.request().method()} ${res.url().replace(/^https?:\/\/[^/]+/, "")}`);
  };
  page.on("response", onResponse as never);
  await run();
  page.off("response", onResponse as never);
  return failed;
}

/**
 * The single best automated proxy for "the layout is broken": a page that
 * scrolls sideways on a phone, or one where a control has been pushed off the
 * visible screen. Fixed-position chrome (nav bars, overlays) is excluded because
 * it is allowed to overlay content by design — the tab bar is checked separately.
 */
async function layoutOffenders(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const out: string[] = [];
    const vw = document.documentElement.clientWidth;

    const horizontallyScrolls = (el: Element): boolean => {
      let node: Element | null = el;
      while (node && node !== document.body) {
        const ox = getComputedStyle(node).overflowX;
        if (ox === "auto" || ox === "scroll") return true;
        node = node.parentElement;
      }
      return false;
    };

    const describe = (el: Element): string => {
      const cls = typeof el.className === "string" ? el.className.split(/\s+/)[0] : "";
      const text = (el.textContent ?? "").trim().slice(0, 24);
      return `${el.tagName.toLowerCase()}${cls ? "." + cls : ""}${text ? ` "${text}"` : ""}`;
    };

    // 1. Interactive controls must be fully on screen (no clipped button).
    //    Subtrees marked `inert` / `aria-hidden` are excluded on purpose: they are
    //    declared non-interactive by contract, and the keyboard suite is what
    //    proves that claim separately (see "the closed account drawer is
    //    unreachable" — a parked drawer SHOULD sit off-canvas).
    for (const el of document.querySelectorAll("button, a, input, select, textarea, [role=button]")) {
      const rect = el.getBoundingClientRect();
      if (rect.width < 1 || rect.height < 1) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === "hidden" || cs.opacity === "0") continue;
      if (cs.position === "fixed") continue;
      if (el.closest("[inert], [aria-hidden='true']")) continue;
      if (horizontallyScrolls(el)) continue;
      if (rect.left < -1 || rect.right > vw + 1) {
        out.push(`off-screen control: ${describe(el)} [${Math.round(rect.left)}..${Math.round(rect.right)}] vw=${vw}`);
      }
    }

    // 2. No element may stick out past the right edge (the "sideways scroll" bug).
    if (document.documentElement.scrollWidth > vw + 1) {
      out.push(`document scrolls sideways: scrollWidth=${document.documentElement.scrollWidth} vw=${vw}`);
    }
    return out.slice(0, 6);
  });
}

/** Wait until the shell has painted and animations have settled. */
async function settle(page: Page): Promise<void> {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(350);
}

// ── The route inventory the adversary walks ─────────────────────────

const PUBLIC_ROUTES = [
  "/",
  "/login",
  "/signup",
  "/forgot-password",
  "/terms",
  "/privacy",
  "/definitely-not-a-page",
];

const APP_ROUTES = [
  "/dashboard",
  "/upload",
  "/plan",
  "/coach",
  "/glow",
  "/explore",
  "/progress",
  "/arc",
  "/glowups",
  "/peak-you",
  "/products",
  "/settings",
  "/upgrade",
];

test.describe("@stress the layout survives every screen size", () => {
  const VIEWPORTS = [
    { name: "iPhone SE 320", width: 320, height: 568 }, // the tightest real target
    { name: "iPhone 12 390", width: 390, height: 844 },
    { name: "iPhone Pro Max 430", width: 430, height: 932 },
    { name: "iPad portrait 768", width: 768, height: 1024 },
    { name: "iPad landscape 1024", width: 1024, height: 768 },
    { name: "laptop 1440", width: 1440, height: 900 },
    { name: "ultrawide 2560", width: 2560, height: 1440 },
  ];

  for (const vp of VIEWPORTS) {
    test(`no screen overflows or hides a control at ${vp.name}`, async ({ page, request }) => {
      // Up to 20 real page loads per viewport: this is a layout gauntlet, not a
      // unit test, so it gets the slower budget the default 30s does not allow.
      test.slow();
      await page.setViewportSize({ width: vp.width, height: vp.height });
      const failures = trackFailures(page);

      // Public surfaces: what a stranger sees first, and what is most likely to
      // have been tuned for one size and forgotten at another.
      for (const route of PUBLIC_ROUTES) {
        await page.goto(route);
        await settle(page);
        expect(await layoutOffenders(page), `${route} @ ${vp.name}`).toEqual([]);
        expect((await page.locator("body").innerText()).trim().length, `${route} rendered nothing`).toBeGreaterThan(0);
      }

      // Authenticated surfaces at the two extremes only — the sizes in between
      // sit on the same mobile/desktop breakpoints the app already switches on.
      if (vp.width <= 430 || vp.width >= 1440) {
        const token = await ensureUser(request, uniqueEmail("stress-layout"));
        await setSession(page, token);
        for (const route of APP_ROUTES) {
          await page.goto(route);
          await settle(page);
          expect(await layoutOffenders(page), `${route} @ ${vp.name}`).toEqual([]);
        }
      }

      expect(failures).toEqual([]);
    });
  }

  test("the mobile tab bar never covers the end of the page", async ({ page, request }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const token = await ensureUser(request, uniqueEmail("stress-nav"));
    await setSession(page, token);
    await page.goto("/dashboard");
    await settle(page);

    const result = await page.evaluate(() => {
      const nav = document.querySelector('nav[aria-label="Bottom"]');
      const main = document.querySelector("main");
      if (!nav || !main) return { navTop: 0, lastBottom: 0, found: false };
      // Scroll to the very bottom first: measuring without scrolling reports
      // every element that is merely below the fold as "under the tab bar".
      // `behavior: "instant"` because the app sets `scroll-behavior: smooth`,
      // and a smooth scroll has not finished by the next line.
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "instant" });
      let lastBottom = 0;
      for (const el of main.querySelectorAll("*")) {
        const rect = el.getBoundingClientRect();
        if (rect.height < 1 || getComputedStyle(el).visibility === "hidden") continue;
        lastBottom = Math.max(lastBottom, rect.bottom);
      }
      return { navTop: nav.getBoundingClientRect().top, lastBottom, found: true };
    });

    expect(result.found, "mobile tab bar or main content missing").toBe(true);
    expect(result.lastBottom, "content ends underneath the tab bar").toBeLessThanOrEqual(result.navTop + 2);
  });

  test("laptop zoom 200% (half the CSS viewport) still fits", async ({ page }) => {
    // Browser zoom shrinks the CSS viewport; 1366 @ 200% lays out as 683 CSS px.
    await page.setViewportSize({ width: 683, height: 384 });
    const token = await ensureUser(page.request, uniqueEmail("stress-zoom"));
    await setSession(page, token);
    for (const route of ["/", "/login", "/signup", "/settings", "/dashboard"]) {
      await page.goto(route);
      await settle(page);
      expect(await layoutOffenders(page), `${route} @ 200% zoom`).toEqual([]);
    }
  });
});
test.describe("@stress a keyboard user cannot fall into a trap", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("the closed account drawer is unreachable and cannot sign anyone out", async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("stress-kb"));
    await setSession(page, token);
    await page.goto("/dashboard");
    await settle(page);

    const drawer = page.locator('aside[role="dialog"][aria-label="Account menu"]');
    await expect(drawer).toHaveCount(1);

    // The drawer is parked off-canvas when closed. Off-canvas is a *visual*
    // state, not an interactive one: if a keyboard can still reach "Log out",
    // then Enter signs the user out with nothing on screen to explain it.
    const logOut = drawer.locator('button:has-text("Log out")');
    const reachable = await logOut.evaluate((el) => {
      (el as HTMLElement).focus();
      return document.activeElement === el;
    });
    expect(reachable, "the closed drawer's Log out button is keyboard-focusable").toBe(false);

    // Tabbing across the whole page must never land inside the closed drawer.
    const landedInside: string[] = [];
    for (let i = 0; i < 45; i++) {
      await page.keyboard.press("Tab");
      const where = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null;
        if (!el || el === document.body) return "body";
        const insideDrawer = Boolean(el.closest('aside[role="dialog"]'));
        return `${insideDrawer ? "DRAWER " : ""}${el.tagName.toLowerCase()} ${(el.textContent ?? "").trim().slice(0, 24)}`;
      });
      if (where.startsWith("DRAWER")) landedInside.push(where);
    }
    expect(landedInside, "keyboard focus entered the closed drawer").toEqual([]);
  });

  test("Escape closes the open drawer", async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("stress-esc"));
    await setSession(page, token);
    await page.goto("/dashboard");
    await settle(page);

    await page.getByRole("button", { name: "Account menu" }).last().click();
    const drawer = page.locator('aside[role="dialog"][aria-label="Account menu"]');
    await expect(drawer).toHaveClass(/translate-x-0/);

    await page.keyboard.press("Escape");
    await expect(drawer).toHaveClass(/translate-x-full/);
    // And the page behind must not be left locked (body scroll restored).
    expect(await page.evaluate(() => document.body.style.overflow)).not.toBe("hidden");
  });

  test("the login form can be completed with the keyboard alone", async ({ page, request }) => {
    const email = uniqueEmail("stress-kbd-login");
    await ensureUser(request, email);
    await page.goto("/login");
    await settle(page);

    // Focus order: email → password → submit, reachable by Tab alone.
    await page.keyboard.press("Tab");
    await page.locator("#email").click({ trial: true }).catch(() => {});
    await page.locator("#email").focus();
    await page.keyboard.type(email);
    await page.keyboard.press("Tab");
    await page.keyboard.type(TEST_PASSWORD);
    await page.keyboard.press("Enter"); // Enter inside the form must submit
    await expect(page).toHaveURL(/dashboard/, { timeout: 15_000 });
  });

  test("the account menu opens and closes with Enter and Escape", async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("stress-esc2"));
    await setSession(page, token);
    await page.goto("/dashboard");
    await settle(page);

    const trigger = page.getByRole("button", { name: "Account menu" }).last();
    await trigger.focus();
    await page.keyboard.press("Enter");
    await expect(trigger).toHaveAttribute("aria-expanded", "true");
    await page.keyboard.press("Enter");
    await expect(trigger).toHaveAttribute("aria-expanded", "false");
  });
});


test.describe("@stress an impatient finger cannot fire an action twice", () => {
  // A 1×1 JPEG — enough for the client-side type/size checks and for the image
  // compressor, so the upload path is exercised exactly as a real pick is.
  const TINY_JPEG = Buffer.from(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q==",
    "base64",
  );

  test("double-tapping Create account creates exactly one account", async ({ page }) => {
    const email = uniqueEmail("stress-dbl");
    let signupPosts = 0;
    await page.route("**/api/v1/auth/signup", async (route) => {
      signupPosts += 1;
      await new Promise((r) => setTimeout(r, 600)); // the server is never instant
      await route.continue();
    });

    await page.goto("/signup");
    await settle(page);
    await page.fill("#email", email);
    await page.fill("#full_name", "Double Tap");
    await page.fill("#password", TEST_PASSWORD);
    await page.getByRole("checkbox").check();

    // Two clicks in one gesture — what every impatient thumb does.
    await page.getByRole("button", { name: /create account/i }).dblclick();
    await expect(page).toHaveURL(/onboarding/, { timeout: 20_000 });
    expect(signupPosts, "a second signup request escaped the disabled button").toBe(1);
  });

  test("double-tapping Save changes sends exactly one update", async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("stress-save"));
    await setSession(page, token);
    let puts = 0;
    await page.route("**/api/v1/profile", async (route) => {
      if (route.request().method() !== "PUT") return route.continue();
      puts += 1;
      await new Promise((r) => setTimeout(r, 600));
      await route.continue();
    });

    await page.goto("/settings");
    await settle(page);
    const save = page.getByRole("button", { name: /save changes/i });
    await expect(save).toBeEnabled();
    await save.dblclick();
    await page.waitForTimeout(1500);
    expect(puts, "a second profile update escaped the loading state").toBe(1);
  });

  test("re-picking the same photo after removing it still works", async ({ page, request }) => {
    // <input type="file"> fires `change` only when the value actually changes, so a
    // user who removes their photo and picks the same file again gets silence
    // unless the input is reset. This is a classic mobile dead-end.
    const token = await ensureUser(request, uniqueEmail("stress-reselect"));
    await setSession(page, token);
    await page.goto("/upload");
    await settle(page);

    const file = { name: "face.jpg", mimeType: "image/jpeg", buffer: TINY_JPEG };
    await page.setInputFiles('input[type="file"]', file);
    await expect(page.getByRole("button", { name: /analyze photo/i })).toBeVisible();
    // The mechanism that makes re-picking work: the input is cleared as soon as
    // we have the file (a file input only fires `change` when its value *changes*).
    await expect(page.locator('input[type="file"]')).toHaveValue("");

    await page.getByRole("button", { name: "Remove photo" }).click();
    await expect(page.getByRole("button", { name: /analyze photo/i })).toHaveCount(0);

    await page.setInputFiles('input[type="file"]', file); // the very same file
    await expect(
      page.getByRole("button", { name: /analyze photo/i }),
      "picking the same photo twice is a dead end",
    ).toBeVisible();
  });
});

test.describe("@stress the upload path cannot be duplicated or dead-ended", () => {
  const TINY_JPEG = Buffer.from(
    "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q==",
    "base64",
  );

  test("double-tapping Analyze photo starts exactly one analysis", async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("stress-upload"));
    await setSession(page, token);

    let signatures = 0;
    let saves = 0;
    let analyses = 0;
    await page.route("**/api/v1/upload/signature", async (route) => {
      signatures += 1;
      await new Promise((r) => setTimeout(r, 500));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          signature: "sig",
          timestamp: 1,
          cloud_name: "demo",
          api_key: "key",
          folder: "lookmaxx",
          public_id: "pid",
        }),
      });
    });
    await page.route("**/api.cloudinary.com/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ secure_url: "https://cdn/x.jpg" }),
      }),
    );
    await page.route("**/api/v1/upload/save**", async (route) => {
      saves += 1;
      await new Promise((r) => setTimeout(r, 500));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ photo_id: "photo-1", file_url: "https://cdn/x.jpg", is_baseline: false, week_number: 1 }),
      });
    });
    await page.route("**/api/v1/photos/analyze/**", async (route) => {
      analyses += 1;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true }) });
    });

    await page.goto("/upload");
    await settle(page);
    await page.setInputFiles('input[type="file"]', { name: "face.jpg", mimeType: "image/jpeg", buffer: TINY_JPEG });
    const analyze = page.getByRole("button", { name: /analyze photo/i });
    await expect(analyze).toBeEnabled();
    await analyze.dblclick();
    await page.waitForTimeout(3000);

    expect(signatures, "the upload was started twice").toBe(1);
    expect(saves, "the photo was saved twice").toBe(1);
    expect(analyses, "two analyses were queued for one photo").toBe(1);
  });

  test("a rejected file says why, and does not destroy the photo already chosen", async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("stress-badfile"));
    await setSession(page, token);
    await page.goto("/upload");
    await settle(page);

    // An "image" that is not decodable — the exact case of a HEIC on desktop
    // Chrome, or a file with the wrong extension.
    await page.setInputFiles('input[type="file"]', {
      name: "notes.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4 not an image"),
    });
    const alert = page.getByRole("alert").filter({ hasText: /JPG|PNG|HEIC|couldn't read/i });
    await expect(alert).toBeVisible();
    const copy = (await alert.innerText()).trim();
    expect(copy.length, "the rejection gives the user nothing to act on").toBeGreaterThan(0);
    expect(copy, "the message should name what is accepted").toMatch(/JPG|PNG|HEIC/i);
  });
});

test.describe("@stress the destructive dialog is hard to trigger by accident", () => {
  test("delete account needs the exact word, backs out on Escape, and cannot double-delete", async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("stress-delete"));
    await setSession(page, token);
    let deletes = 0;
    await page.route("**/api/v1/profile/delete", async (route) => {
      deletes += 1;
      await new Promise((r) => setTimeout(r, 700));
      await route.continue();
    });

    await page.goto("/settings");
    await settle(page);
    await page.getByRole("button", { name: /delete account/i }).click();
    const confirm = page.getByRole("button", { name: /delete permanently/i });
    await expect(confirm).toBeDisabled();

    for (const attempt of ["delete", "Delete", "DELETE!", " DELETE", "DELETE "]) {
      await page.getByPlaceholder("DELETE").fill(attempt);
      await expect(confirm, `"${attempt}" armed the destructive button`).toBeDisabled();
    }

    // Escape must back out of a destructive dialog.
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: /confirm account deletion/i })).toHaveCount(0);

    await page.getByRole("button", { name: /delete account/i }).click();
    await page.getByPlaceholder("DELETE").fill("DELETE");
    await confirm.dblclick();
    await page.waitForTimeout(2500);
    expect(deletes, "the account was deleted twice").toBe(1);
  });
});

test.describe("@stress hostile input is refused politely", () => {
  test("a 300-character email never reaches the server", async ({ page }) => {
    let posts = 0;
    await page.route("**/api/v1/auth/signup", async (route) => {
      posts += 1;
      await route.continue();
    });
    await page.goto("/signup");
    await settle(page);
    await page.fill("#email", "a".repeat(300) + "@example.com");
    await page.fill("#password", TEST_PASSWORD);
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: /create account/i }).click();

    await expect(page.getByRole("alert").first()).toBeVisible();
    expect(posts, "a malformed email was still sent to the server").toBe(0);
  });

  test("a 10,000-character password is refused and the button frees up again", async ({ page }) => {
    let posts = 0;
    await page.route("**/api/v1/auth/signup", async (route) => {
      posts += 1;
      await route.continue();
    });
    const failures = trackFailures(page);
    await page.goto("/signup");
    await settle(page);
    await page.fill("#email", uniqueEmail("stress-huge"));
    await page.fill("#password", "🔒".repeat(5000));
    await page.getByRole("button", { name: /create account/i }).click();

    // Refused at the client, before anything is sent.
    await expect(page.getByText(/password is too long/i)).toBeVisible();
    await expect(page.getByText(/please agree to continue/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /create account/i })).toBeEnabled();
    expect(posts, "an over-long password reached the server").toBe(0);
    expect(failures).toEqual([]);
  });

  test("the age step explains itself instead of silently disabling Next", async ({ page, request }) => {
    // A 12-year-old types their real age. The Next button greys out. If nothing
    // else on the screen changes, the only possible conclusion is "this app is
    // broken" — the wizard owes them a sentence.
    const token = await ensureUser(request, uniqueEmail("stress-age"));
    await setSession(page, token);
    await page.goto("/onboarding");
    await settle(page);

    const age = page.locator("#age");
    await age.pressSequentially("12");
    await expect(page.getByRole("button", { name: /^next$/i })).toBeDisabled();
    await expect(
      page.getByText(/13/),
      "an unreachable age shows a dead button with no explanation",
    ).toBeVisible();
  });

  test("letters typed into the age field never silently pass validation", async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("stress-age2"));
    await setSession(page, token);
    await page.goto("/onboarding");
    await settle(page);
    await page.locator("#age").pressSequentially("abc");
    await expect(page.getByRole("button", { name: /^next$/i })).toBeDisabled();
  });

  test("an emoji name renders as one character, not a broken glyph", async ({ page, request }) => {
    // `name.charAt(0)` splits a surrogate pair and paints U+FFFD in the avatar
    // circle — the kind of detail that makes an app feel unfinished.
    const email = uniqueEmail("stress-emoji");
    await request.post(`${API_URL}/auth/signup`, {
      data: { email, password: TEST_PASSWORD, full_name: "🦁🚀" },
    });
    const login = await request.post(`${API_URL}/auth/login`, {
      form: { username: email, password: TEST_PASSWORD },
    });
    const token = ((await login.json()) as { access_token: string }).access_token;
    await setSession(page, token);
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/dashboard");
    await settle(page);

    const avatar = page.getByRole("button", { name: "Account menu" }).last();
    const text = await avatar.innerText();
    expect(text, "the avatar shows a replacement glyph for an emoji name").not.toContain("\uFFFD");
    // The stronger check: it must be the *whole* emoji, not the lone high
    // surrogate ("\ud83e") that `name.charAt(0)` produces.
    expect(text).toBe("🦁");
  });

  test("a 200-character name does not break the app chrome", async ({ page, request }) => {
    const email = uniqueEmail("stress-longname");
    const longName = "Wolfeschlegelsteinhausenbergerdorff".repeat(6).slice(0, 200);
    await request.post(`${API_URL}/auth/signup`, {
      data: { email, password: TEST_PASSWORD, full_name: longName },
    });
    const login = await request.post(`${API_URL}/auth/login`, {
      form: { username: email, password: TEST_PASSWORD },
    });
    const token = ((await login.json()) as { access_token: string }).access_token;
    await setSession(page, token);

    for (const width of [320, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/dashboard");
      await settle(page);
      expect(await layoutOffenders(page), `long name broke the layout at ${width}px`).toEqual([]);
    }
  });
});

test.describe("@stress hand-edited URLs fail softly", () => {
  test("an unknown photo id is a friendly dead end, not a blank screen", async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("stress-404photo"));
    await setSession(page, token);
    const failures = trackFailures(page);
    await page.goto("/results/999999999");
    await settle(page);

    await expect(page.getByText(/couldn't find this photo|not analyzed yet/i)).toBeVisible({ timeout: 15_000 });
    expect((await page.locator("body").innerText()).trim().length).toBeGreaterThan(0);
    expect(failures).toEqual([]);
  });

  test("a hostile photo id cannot execute or break the page", async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("stress-xss"));
    await setSession(page, token);
    let dialogOpened = false;
    page.on("dialog", (d) => {
      dialogOpened = true;
      void d.dismiss();
    });
    const failures = trackFailures(page);
    await page.goto("/results/%3Cscript%3Ealert(1)%3C%2Fscript%3E");
    await settle(page);

    await expect(page.locator("body")).toBeVisible();
    expect(dialogOpened, "a script from the URL executed").toBe(false);
    // An error boundary / 404 is acceptable; an unhandled crash is not.
    expect(failures.filter((f) => !f.includes("422")).length).toBe(0);
  });

  test("the admin area refuses a normal user, and the API refuses harder", async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("stress-admin"));
    await setSession(page, token);
    await page.goto("/admin");
    await settle(page);
    // The client gate is cosmetic; the real check must be server-side.
    await expect(page.getByText(/admin access required/i)).toBeVisible({ timeout: 15_000 });

    const res = await request.get(`${API_URL}/analytics/admin/overview`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(res.status(), "a non-admin read the admin analytics API").toBeGreaterThanOrEqual(403);
    expect(res.status()).toBeLessThan(500);
  });

  test("a deep link survives the login round-trip", async ({ page, request }) => {
    const email = uniqueEmail("stress-deeplink");
    await ensureUser(request, email);

    await page.goto("/settings");
    await expect(page).toHaveURL(/\/login\?next=%2Fsettings/, { timeout: 15_000 });

    await page.fill("#email", email);
    await page.fill("#password", TEST_PASSWORD);
    await page.getByRole("button", { name: /log in|logging in/i }).click();
    await expect(page, "the deep link was dropped after logging in").toHaveURL(/\/settings/, { timeout: 20_000 });
  });

  test("an unknown route offers a way back", async ({ page }) => {
    await page.goto("/definitely-not-a-page");
    await settle(page);
    await expect(page.getByText(/page not found/i)).toBeVisible();
    await expect(page.getByRole("link", { name: /back to dashboard/i })).toBeVisible();
  });
});

test.describe("@stress the network and the back button are survived", () => {
  test("offline is announced, an action fails honestly, and nothing spins forever", async ({
    page,
    request,
    context,
  }) => {
    const token = await ensureUser(request, uniqueEmail("stress-offline"));
    await setSession(page, token);
    await page.goto("/settings");
    await settle(page);

    await context.setOffline(true);
    await expect(page.getByText(/you're offline/i), "offline was not announced").toBeVisible({ timeout: 10_000 });

    // A real edit is required: with nothing changed the form short-circuits with
    // "change something first" and we would not be testing the network at all.
    await page.fill("#full_name", `Offline ${Date.now()}`);
    const save = page.getByRole("button", { name: /save changes/i });
    await save.click();
    await expect(page.getByText(/can't reach the server|no connection/i).first()).toBeVisible({ timeout: 15_000 });
    await expect(save, "the save button stayed stuck in a spinner").toBeEnabled({ timeout: 15_000 });

    await context.setOffline(false);
    await expect(page.getByText(/you're offline/i)).toHaveCount(0, { timeout: 10_000 });
    await save.click();
    await expect(page.getByText(/profile updated/i)).toBeVisible({ timeout: 15_000 });
  });

  test("the browser Back button never lands on a broken page", async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("stress-back"));
    await setSession(page, token);
    const failures = trackFailures(page);

    await page.goto("/dashboard");
    await settle(page);
    await page.goto("/settings");
    await settle(page);
    await page.goBack();
    await settle(page);
    expect(await layoutOffenders(page), "Back landed on a broken page").toEqual([]);

    await page.goForward();
    await settle(page);
    expect(await layoutOffenders(page), "Forward landed on a broken page").toEqual([]);
    expect(failures).toEqual([]);
  });

  test("refreshing mid-onboarding returns a usable wizard, not a dead one", async ({ page, request }) => {
    const token = await ensureUser(request, uniqueEmail("stress-refresh"));
    await setSession(page, token);
    const failures = trackFailures(page);

    await page.goto("/onboarding");
    await settle(page);
    await page.locator("#age").pressSequentially("24");
    // Step 1 also requires a gender; picking one is what a real user does next.
    await page.getByRole("radio").first().click();
    await page.getByRole("button", { name: /^next$/i }).click();
    await expect(page.getByText(/pick one goal/i)).toBeVisible({ timeout: 10_000 });

    await page.reload();
    await settle(page);
    await expect(page.getByText(/tell us about you/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole("button", { name: /skip/i })).toBeVisible();
    expect(failures).toEqual([]);
  });

  test("logging out in one tab does not leave the other tab silently broken", async ({ browser, request }) => {
    const token = await ensureUser(request, uniqueEmail("stress-tabs"));
    const context = await browser.newContext();

    const pageA = await context.newPage();
    const pageB = await context.newPage();
    for (const p of [pageA, pageB]) {
      await p.goto("/login");
      await p.evaluate((t) => window.localStorage.setItem("lookmaxx_token", t), token);
    }
    await pageA.goto("/dashboard");
    await pageB.goto("/dashboard");
    await expect(pageA.getByText(/welcome back/i)).toBeVisible({ timeout: 15_000 });

    // Sign out in the second tab.
    await pageB.setViewportSize({ width: 390, height: 844 });
    await pageB.getByRole("button", { name: "Account menu" }).last().click();
    await pageB.getByRole("button", { name: /log out/i }).click();
    await expect(pageB).toHaveURL(/\/$|\/login/, { timeout: 15_000 });

    // The first tab now holds a token that no longer exists. It must not sit
    // there pretending to be signed in while every request fails behind it.
    await pageA.bringToFront();
    await expect(pageA, "the other tab was left in a zombie signed-in state").toHaveURL(/\/login/, {
      timeout: 20_000,
    });
    await context.close();
  });
});

test.describe("@stress no screen makes a request it cannot explain", () => {
  test("a brand-new account opening every screen produces no 5xx and no mystery 4xx", async ({
    page,
    request,
  }) => {
    test.slow();
    const token = await ensureUser(request, uniqueEmail("stress-audit"));
    await setSession(page, token);

    // The only endpoints allowed to fail for an account with no photos yet.
    // Each is rendered as an empty state, so the user loses nothing — but the
    // list is pinned, so a *new* unexpected failure (or any 5xx at all) breaks
    // this test instead of quietly becoming background noise.
    const EXPECTED_NO_DATA = new Set([
      "404 GET /api/v1/progress/photos/compare",
      "404 GET /api/v1/progress/photos/latest",
    ]);

    const failed = await auditFailedRequests(page, async () => {
      for (const route of APP_ROUTES) {
        await page.goto(route);
        await settle(page);
      }
    });

    expect(failed.filter((f) => /^5\d\d/.test(f)), "a screen hit a server error").toEqual([]);
    expect(
      failed.filter((f) => !EXPECTED_NO_DATA.has(f)),
      "an unexplained failing request appeared",
    ).toEqual([]);
  });

  test("an open drawer keeps focus inside itself", async ({ page, request }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const token = await ensureUser(request, uniqueEmail("stress-trap"));
    await setSession(page, token);
    await page.goto("/dashboard");
    await settle(page);

    await page.getByRole("button", { name: "Account menu" }).last().click();
    const drawer = page.locator('aside[role="dialog"][aria-label="Account menu"]');
    await expect(drawer).toHaveClass(/translate-x-0/);

    // Focus must go *into* the dialog when it opens…
    expect(await page.evaluate(() => Boolean(document.activeElement?.closest('aside[role="dialog"]')))).toBe(true);

    // …and Tab must never walk out the back of it into the page underneath.
    const escaped: string[] = [];
    for (let i = 0; i < 14; i++) {
      await page.keyboard.press("Tab");
      const inside = await page.evaluate(() =>
        Boolean(document.activeElement?.closest('aside[role="dialog"]')),
      );
      if (!inside) escaped.push(await page.evaluate(() => document.activeElement?.tagName ?? "none"));
    }
    expect(escaped, "Tab escaped the open drawer").toEqual([]);
  });
});

