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

  test("an eligible member lands on the £1 price with no interaction", async ({ page }) => {
    await stubApi(page, { offer: eligibleOffer });
    await page.goto("/upgrade");

    const proCard = page.locator("div.rounded-card", {
      has: page.getByRole("heading", { name: "Pro" }),
    });
    // The coupon prices the Pro *monthly* plan, so eligibility has to land there.
    // Leaving the annual default in place is what made the launch offer look
    // missing: the card headlined £4.20/mo (list £9.99, struck) + "Start Pro".
    await expect(proCard).toContainText("£1.00");
    await expect(proCard).toContainText("first month");
    await expect(proCard).toContainText("Then £9.99/month from month 2");
    // The CTA states the amount charged, matching the card headline.
    await expect(proCard.getByRole("button", { name: "Start for £1.00" })).toBeVisible();
    await expect(proCard.getByRole("button", { name: "Start Pro" })).toHaveCount(0);
  });

  test("choosing annual keeps the £1 offer one tap away", async ({ page }) => {
    await stubApi(page, { offer: eligibleOffer });
    await page.goto("/upgrade");
    await page.getByRole("button", { name: /^Annual/ }).click();

    const proCard = page.locator("div.rounded-card", {
      has: page.getByRole("heading", { name: "Pro" }),
    });
    // Annual figures, because an annual plan is not eligible for a
    // `duration=once` coupon — the card must not imply otherwise.
    await expect(proCard).toContainText("£50.40/yr");
    await expect(proCard).not.toContainText("Then £9.99/month from month 2");

    // …and the offer is a real button, not a link nobody scanning a price scans.
    const switchToMonthly = proCard.getByRole("button", {
      name: /Switch to monthly for a £1\.00 first month/,
    });
    await expect(switchToMonthly).toBeVisible();

    await switchToMonthly.click();
    await expect(proCard.getByRole("button", { name: "Start for £1.00" })).toBeVisible();
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
    await expect(proCard).toContainText("£50.40/yr");
    await expect(proCard).not.toContainText("Then £9.99/month from month 2");
  });

  test("no price is printed until the server has answered", async ({ page }) => {
    await stubApi(page, { offer: eligibleOffer, offerDelayMs: 2500 });
    await page.goto("/upgrade");

    const proCard = page.locator("div.rounded-card", {
      has: page.getByRole("heading", { name: "Pro" }),
    });
    // While /payments/offer is in flight neither price may be claimed: printing
    // £9.99 and then replacing it with £1.00 is the DEF-015 mismatch as a flash.
    await expect(proCard).toContainText("Checking your price…");
    await expect(proCard).not.toContainText("9.99");

    await expect(proCard).toContainText("£1.00");
    await expect(proCard).not.toContainText("Checking your price…");
  });

  test("a used offer is never advertised again", async ({ page }) => {
    await stubApi(page, {
      me: { ...ME_FREE, has_used_first_month_offer: true },
      offer: { ...eligibleOffer, eligible: false, reason: "used" },
    });
    await page.goto("/upgrade");
    await page.getByRole("button", { name: "Monthly", exact: true }).click();

    const proCard = page.locator("div.rounded-card", {
      has: page.getByRole("heading", { name: "Pro" }),
    });
    await expect(proCard).toContainText("£9.99");
    await expect(proCard).toContainText("Your £1 first month has already been used.");
    await expect(proCard).not.toContainText("Then £9.99/month from month 2");
    await expect(proCard.getByRole("button", { name: "Start for £1.00" })).toHaveCount(0);
  });

  test("no offer configured means list pricing, with no £1 claim anywhere", async ({ page }) => {
    await stubApi(page, {});
    await page.goto("/upgrade");
    await page.getByRole("button", { name: "Monthly", exact: true }).click();

    await expect(page.getByText("first month", { exact: false })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Start Pro" })).toBeVisible();
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