import { test, expect, type Page } from "@playwright/test";

/**
 * Score + price honesty (DEF-014, DEF-015).
 *
 * Both bugs were "the UI printed a number that wasn't true":
 *   - DEF-014: an analysis that couldn't load MediaPipe scored synthetic
 *     landmarks, whose symmetry clamps to exactly 0 → "Symmetry 0" on a real face.
 *   - DEF-015: the upgrade page hardcoded £9.99 while Stripe charged £1, and the
 *     post-checkout redirect landed on a page that showed neither amount.
 *
 * The API is stubbed here on purpose: that is the only way to assert the UI
 * *renders* what the server reports, deterministically, without MediaPipe or a
 * real Stripe session. The backend's own guarantees are covered by
 * `backend/tests/test_symmetry_pipeline.py` and `test_payments.py`.
 */

// Intercepted responses are subject to the browser's CORS checks, so every
// fulfilled reply carries the header (the real API is cross-origin too).
const CORS = { "access-control-allow-origin": "*" };

const ME_FREE = {
  id: "u1",
  email: "free@example.com",
  full_name: "Free User",
  onboarding_completed: true,
  subscription_tier: "free",
  is_subscribed: false,
  is_admin: false,
  has_used_first_month_offer: false,
  subscription_end: null,
  subscription_cancels_at_period_end: false,
  total_checkins: 0,
  current_streak: 0,
  longest_streak: 0,
  current_day: 0,
  created_at: "2026-01-01T00:00:00",
};

const STATUS = {
  id: "p1",
  analysis_status: "completed",
  score: 71,
  potential_score: 80,
  strengths: ["Good skin clarity"],
  weaknesses: [],
  error: null,
  message: null,
  category_breakdown: null,
  raw_score: null,
  model_used: false,
  improvement_potential: null,
};

async function stubApi(
  page: Page,
  handlers: {
    me?: unknown;
    analysis?: unknown;
    offer?: unknown;
    receipt?: unknown;
    /** Hold /payments/offer open, to pin what the card shows while undecided. */
    offerDelayMs?: number;
    /** Reply for POST /payments/checkout. Default `{}` → no URL → waitlist path. */
    checkout?: unknown;
    /** Collects POST /payments/checkout bodies, so a click can be asserted on. */
    checkoutBodies?: unknown[];
  },
) {
  await page.route("**/api/v1/**", async (route) => {
    const url = route.request().url();
    const json = (body: unknown) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: CORS,
        body: JSON.stringify(body),
      });

    if (url.includes("/auth/me")) return json(handlers.me ?? ME_FREE);
    if (url.includes("/payments/offer")) {
      if (handlers.offerDelayMs) {
        await new Promise((resolve) => setTimeout(resolve, handlers.offerDelayMs));
      }
      return json(handlers.offer ?? { eligible: false, reason: "not_configured" });
    }
    if (url.includes("/payments/checkout/")) return json(handlers.receipt ?? {});
    // The POST carries no trailing slash; the receipt GET above does.
    if (url.endsWith("/payments/checkout")) {
      handlers.checkoutBodies?.push(route.request().postDataJSON());
      return json(handlers.checkout ?? {});
    }
    if (url.includes("/analysis/") && url.includes("/insights")) return json({});
    if (url.includes("/analysis/")) return json(handlers.analysis ?? {});
    if (url.includes("/status")) return json(STATUS);
    return json({});
  });
}

test.describe("a score that was never measured (DEF-014)", () => {
  const analysis = {
    photo_id: "p1",
    file_url: "",
    // The API now returns null — not 0 — for a score it could not measure.
    scores: { overall: 71, symmetry: null, skin: 67, jawline: 43, eyes: 37 },
    face_shape: null,
    is_baseline: true,
    analyzed_at: null,
    measurement: {
      landmarks: "unavailable",
      measured: false,
      reason: "MediaPipe face-landmark model unavailable",
      not_measured: ["symmetry"],
    },
  };

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => window.localStorage.setItem("lookmaxx_token", "stub-token"));
    await stubApi(page, { analysis });
  });

  test("renders a dash, never a fabricated 0, for the unmeasured row", async ({ page }) => {
    await page.goto("/results/p1");

    const breakdown = page.locator("div.rounded-card", {
      has: page.getByRole("heading", { name: "Breakdown" }),
    });
    const symmetryRow = breakdown.locator("div.mb-1").filter({ hasText: "Symmetry" });

    await expect(symmetryRow).toBeVisible();
    await expect(symmetryRow).toContainText("—");
    // A measured row renders a `tabular` number span; this one must not.
    await expect(symmetryRow.locator("span.tabular")).toHaveCount(0);

    // The rows that *were* measured still show their numbers.
    await expect(breakdown.locator("div.mb-1").filter({ hasText: "Skin" })).toContainText("67");
  });

  test("explains why the row is empty instead of leaving it looking broken", async ({ page }) => {
    await page.goto("/results/p1");

    await expect(
      page.getByText("We couldn't read your facial landmarks", { exact: false }),
    ).toBeVisible();
  });

  test("a free member with an analysis still gets the Pro lock on gated surfaces", async ({
    page,
  }) => {
    // /glow-up and /peak-you show their Pro lock only once an analysis exists;
    // this pins that locked state without needing MediaPipe or a real photo (the
    // API-driven e2e suite can't produce a measured analysis locally).
    await page.route("**/api/v1/progress/photos/latest", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: CORS,
        body: JSON.stringify({
          id: "p1",
          file_url: "",
          score: 71,
          is_baseline: true,
          week_number: 1,
          captured_at: null,
        }),
      }),
    );

    for (const path of ["/glow-up", "/peak-you"]) {
      await page.goto(path);
      await expect(page.getByText("Upgrade to Pro").first()).toBeVisible();
      await expect(page.getByText("No analysis yet")).toHaveCount(0);
    }
  });
});

test.describe("the £1 first month is server-authoritative (DEF-015)", () => {
  const eligibleOffer = {
    eligible: true,
    reason: "eligible",
    tier: "pro",
    interval: "month",
    currency: "GBP",
    first_month_amount: 1,
    first_month_amount_minor: 100,
    regular_amount: 9.99,
    regular_amount_minor: 999,
    source: "stripe",
    verified: true,
  };

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => window.localStorage.setItem("lookmaxx_token", "stub-token"));
  });

  test("an eligible member sees the £1 banner with no interaction (DEF-016)", async ({ page }) => {
    await stubApi(page, { offer: eligibleOffer });
    await page.goto("/upgrade");

    // DEF-017: the launch offer is the page's loudest element, above the cards.
    // The regression this guards is the offer *existing* but reading as a
    // footnote inside a £9.99 price card.
    const banner = page.getByRole("region", { name: /Get started for £1\.00/ });
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("First month special");
    await expect(banner).toContainText("then £9.99/month from month 2");
    await expect(banner.getByRole("button", { name: "Start for £1.00" })).toBeVisible();

    // …and the cards stay price cards: regular numbers, no £1 headline.
    const proCard = page.locator("div.rounded-card", {
      has: page.getByRole("heading", { name: "Pro" }),
    });
    await expect(proCard).toContainText("£9.99");
    await expect(proCard).not.toContainText("first month");
    // The card's CTA still states the amount charged — the number on the button
    // is the number Stripe takes (DEF-015), even though the price block above it
    // shows the regular monthly price.
    await expect(proCard.getByRole("button", { name: "Start for £1.00" })).toBeVisible();
  });

  test("the banner CTA buys the monthly Pro plan with the coupon attached", async ({ page }) => {
    const bodies: unknown[] = [];
    await stubApi(page, { offer: eligibleOffer, checkoutBodies: bodies });
    await page.goto("/upgrade");

    const banner = page.getByRole("region", { name: /Get started for £1\.00/ });
    await banner.getByRole("button", { name: "Start for £1.00" }).click();

    // The coupon is `duration=once` on the Pro *monthly* price. Sending
    // annual: true here is the bug that would charge £50.40 instead of £1.
    expect(bodies).toHaveLength(1);
    expect(bodies[0]).toEqual({ tier: "pro", annual: false, first_month_offer: true });

    // The stub hands back no checkout URL (it must not send the test browser to
    // the real checkout.stripe.com), so the page stops at the waitlist copy.
    await expect(page.getByText(/waitlist/)).toBeVisible();
  });

  test("in the annual view the banner still sells the £1 first month", async ({ page }) => {
    await stubApi(page, { offer: eligibleOffer });
    await page.goto("/upgrade");
    await page.getByRole("button", { name: /^Annual/ }).click();

    const proCard = page.locator("div.rounded-card", {
      has: page.getByRole("heading", { name: "Pro" }),
    });
    // Annual figures, because an annual plan is not eligible for a
    // `duration=once` coupon — the card must not imply otherwise.
    await expect(proCard).toContainText("£50.40/yr");
    await expect(proCard).not.toContainText("first month");
    // And its button must not promise £1 while it would buy the annual plan.
    await expect(proCard.getByRole("button", { name: "Start Pro" })).toBeVisible();

    // DEF-017: the offer no longer needs an in-card "switch to monthly" button —
    // the banner is present in every view, so it is always one tap away.
    await expect(page.getByRole("region", { name: /Get started for £1\.00/ })).toBeVisible();
  });

  test("a view the visitor picked is never overwritten by the eligibility default", async ({
    page,
  }) => {
    // The offer resolves *after* the click, which is exactly when a naive effect
    // would flip the toggle back to monthly and silently re-price the card.
    await stubApi(page, { offer: eligibleOffer, offerDelayMs: 1200 });
    await page.goto("/upgrade");
    await page.getByRole("button", { name: /^Annual/ }).click();

    const proCard = page.locator("div.rounded-card", {
      has: page.getByRole("heading", { name: "Pro" }),
    });
    // The banner lands in its own slot above the cards; the card it must never
    // touch keeps showing the annual figures the visitor chose.
    await expect(page.getByRole("region", { name: /Get started for £1\.00/ })).toBeVisible();
    await expect(proCard).toContainText("£50.40/yr");
    await expect(proCard).not.toContainText("first month");
  });

  test("the offer slot holds its place, and the card price never changes", async ({ page }) => {
    await stubApi(page, { offer: eligibleOffer, offerDelayMs: 2500 });
    await page.goto("/upgrade");

    const proCard = page.locator("div.rounded-card", {
      has: page.getByRole("heading", { name: "Pro" }),
    });
    // While /payments/offer is in flight the offer slot says so, and the card is
    // already showing the price it will keep. A card that flips £9.99 → £1.00 is
    // the DEF-015 mismatch as a flash — which is why the offer never moves it.
    await expect(page.getByText("Checking your offer…")).toBeVisible();
    await expect(proCard).toContainText("£9.99");
    await expect(page.getByRole("region", { name: /Get started for £1\.00/ })).toHaveCount(0);

    await expect(page.getByRole("region", { name: /Get started for £1\.00/ })).toBeVisible();
    await expect(page.getByText("Checking your offer…")).toHaveCount(0);
    await expect(proCard).toContainText("£9.99");
  });

  test("a used offer is never advertised again", async ({ page }) => {
    await stubApi(page, {
      me: { ...ME_FREE, has_used_first_month_offer: true },
      offer: { ...eligibleOffer, eligible: false, reason: "used" },
    });
    await page.goto("/upgrade");
    await page.getByRole("button", { name: "Monthly", exact: true }).click();

    await expect(page.getByRole("region", { name: /Get started for/ })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Start for £1.00" })).toHaveCount(0);

    const proCard = page.locator("div.rounded-card", {
      has: page.getByRole("heading", { name: "Pro" }),
    });
    await expect(proCard).toContainText("£9.99");
    await expect(proCard).toContainText("Your £1 first month has already been used.");
  });

  test("an offer Stripe can't confirm is announced as unavailable, never as £1", async ({
    page,
  }) => {
    // The live-mode trap: the coupon exists in the test account only, so the
    // account is eligible but the offer is unverifiable. Printing £1 here is how
    // a customer walks into Stripe and gets billed £9.99 — say so instead.
    await stubApi(page, {
      offer: { ...eligibleOffer, verified: false, source: "config" },
    });
    await page.goto("/upgrade");
    await page.getByRole("button", { name: "Monthly", exact: true }).click();

    await expect(
      page.getByText("The £1.00 first-month offer is temporarily unavailable"),
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Start for £1.00" })).toHaveCount(0);

    const proCard = page.locator("div.rounded-card", {
      has: page.getByRole("heading", { name: "Pro" }),
    });
    await expect(proCard).toContainText("£9.99");
    await expect(proCard.getByRole("button", { name: "Start Pro" })).toBeVisible();
  });

  test("no offer configured means list pricing, with no £1 claim anywhere", async ({ page }) => {
    await stubApi(page, {});
    await page.goto("/upgrade");
    await page.getByRole("button", { name: "Monthly", exact: true }).click();

    await expect(page.getByText("first month", { exact: false })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Start Pro" })).toBeVisible();
  });

  test("a Pro subscriber sees the Elite upgrade, never the launch offer", async ({ page }) => {
    await stubApi(page, { me: { ...ME_FREE, subscription_tier: "pro", is_subscribed: true } });
    await page.goto("/upgrade");
    await page.getByRole("button", { name: "Monthly", exact: true }).click();

    // No banner for a paying customer: the offer is a first-month acquisition
    // price, and /payments/offer is not even consulted once tier !== free.
    await expect(page.getByRole("region", { name: /Get started for/ })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Start for £1.00" })).toHaveCount(0);

    const proCard = page.locator("div.rounded-card", {
      has: page.getByRole("heading", { name: "Pro" }),
    });
    await expect(proCard.getByRole("button", { name: "Current plan" })).toBeVisible();

    const eliteCard = page.locator("div.rounded-card", {
      has: page.getByRole("heading", { name: "Elite" }),
    });
    await expect(eliteCard.getByRole("button", { name: "Switch to Elite" })).toBeVisible();
  });

  test("an Elite subscriber gets no upgrade CTA at all", async ({ page }) => {
    await stubApi(page, { me: { ...ME_FREE, subscription_tier: "elite", is_subscribed: true } });
    await page.goto("/upgrade");

    await expect(page.getByText("You're already on Elite.")).toBeVisible();
    await expect(page.getByRole("region", { name: /Get started for/ })).toHaveCount(0);

    const eliteCard = page.locator("div.rounded-card", {
      has: page.getByRole("heading", { name: "Elite" }),
    });
    await expect(eliteCard.getByRole("button", { name: "Current plan" })).toBeVisible();
    // "Switch to Elite" must be gone: there is nothing above Elite to buy.
    await expect(page.getByRole("button", { name: "Switch to Elite" })).toHaveCount(0);
  });
});

test.describe("the receipt shows what Stripe actually charged (DEF-015)", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => window.localStorage.setItem("lookmaxx_token", "stub-token"));
  });

  test("first-month charge is reported as £1.00 with the discount", async ({ page }) => {
    await stubApi(page, {
      receipt: {
        status: "complete",
        paid: true,
        tier: "pro",
        interval: "month",
        currency: "GBP",
        amount_charged: 1,
        amount_charged_minor: 100,
        amount_discount: 8.99,
        amount_discount_minor: 899,
        first_month_offer: true,
        next_payment_amount: 9.99,
        next_payment_amount_minor: 999,
        next_payment_date: "2026-10-16T12:00:00",
        email: "buyer@example.com",
      },
    });

    await page.goto("/upgrade/success?session_id=cs_test_ok");

    await expect(page.getByText("You were charged £1.00", { exact: false })).toBeVisible();
    await expect(page.getByText("Discount applied")).toBeVisible();
    await expect(page.getByText("−£8.99")).toBeVisible();
    await expect(page.getByText("Next payment (16 October 2026)")).toBeVisible();
    await expect(page.getByText("£9.99/mo")).toBeVisible();
    await expect(page.getByText("A receipt is on its way to buyer@example.com")).toBeVisible();
  });

  test("a full-price charge never claims the offer price", async ({ page }) => {
    await stubApi(page, {
      receipt: {
        status: "complete",
        paid: true,
        tier: "pro",
        interval: "month",
        currency: "GBP",
        amount_charged: 9.99,
        amount_charged_minor: 999,
        amount_discount: null,
        amount_discount_minor: null,
        first_month_offer: false,
        next_payment_amount: 9.99,
        next_payment_amount_minor: 999,
        next_payment_date: "2026-10-16T12:00:00",
        email: "buyer@example.com",
      },
    });

    await page.goto("/upgrade/success?session_id=cs_test_full");

    await expect(page.getByText("You were charged £9.99", { exact: false })).toBeVisible();
    await expect(page.getByText("You were charged £1.00", { exact: false })).toHaveCount(0);
    await expect(page.getByText("Discount applied")).toHaveCount(0);
  });
});

test.describe("the score reveal survives reduced motion (experience system §2.3)", () => {
  // The reveal sequences three beats: the ring fills and the number counts →
  // the ring pops with a gold flare → the verdict label rises in 340ms later.
  // Motion is never load-bearing (PSYCHOLOGY.md §2.3), so these pin the two
  // ways that promise can silently break: the label rendered *before* the
  // number (simultaneity instead of sequencing), and a reduced-motion user
  // losing the label because someone changed the animation's fill mode.
  const analysis = {
    photo_id: "p1",
    file_url: "",
    scores: { overall: 71, symmetry: 68, skin: 74, jawline: 63, eyes: 70 },
    face_shape: "oval",
    is_baseline: true,
    analyzed_at: "2026-09-17T00:00:00",
    measurement: { landmarks: "available", measured: true, reason: null, not_measured: [] },
  };

  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => window.localStorage.setItem("lookmaxx_token", "stub-token"));
    await stubApi(page, { analysis });
  });

  test("the verdict never precedes the number it judges", async ({ page }) => {
    await page.goto("/results/p1");

    // Checked in the same tick as the first paint: a slow hydration can only
    // make this pass (the label isn't mounted yet), so it fails for exactly one
    // reason — the label being rendered alongside the ring.
    await expect(page.getByText("Strong features")).toHaveCount(0);

    // …and it does arrive, once the count has landed.
    await expect(page.getByText("Strong features")).toBeVisible({ timeout: 5000 });
    await expect(page.getByText("71", { exact: true })).toBeVisible();
  });

  test("with reduced motion the score and its verdict are on screen at once", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/results/p1");

    // No count-up, no flare, no 340ms delay — but nothing is missing either.
    await expect(page.getByText("71", { exact: true })).toBeVisible();
    await expect(page.getByText("Strong features")).toBeVisible();
  });
});
