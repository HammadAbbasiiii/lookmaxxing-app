# Test Results — LookMaxx

> Phase 38 deliverable. Evidence-based; no "bug-free" / "secure" claims.

## Metadata
- **Date:** 2026-09-06
- **Commit:** `c9229f5` (+ local testing/fix changes, uncommitted)
- **Environment:** macOS (darwin), Python 3.12 venv (backend), Node 26 / Next 15.5.25 (frontend), local SQLite (`e2e.db`), local servers on `127.0.0.1:8000` + `localhost:3000`.
- **Browser matrix:** Chromium 153, Firefox (Playwright), WebKit 26.6.
- **Viewport matrix:** 1920×1080, 1440×900, 1280×720, 1024×768, 768×1024, 430×932, 390×844, 375×667.

## Totals
| Suite | Passed | Failed | Skipped | Blocked |
|---|---|---|---|---|
| Backend pytest (unit/API/security) | 261 | 0 | 0 | 0 |
| E2E — Chromium (full) | 43 | 0 | 0 | 0 |
| E2E — cross-browser critical (Firefox 9 + WebKit 9) | 18 | 0 | 0 | 0 |
| **Total executions** | **322** | **0** | **0** | **0** |

- Frontend `tsc --noEmit`: clean.
- Frontend `next build`: clean (all routes compile).

> **Environment gotcha (not an app defect):** running `next build` against the
> same `.next` directory while a live `next dev` server is running clobbers the
> dev server and causes stale/broken routes + timeouts in a subsequent E2E run.
> Always restart `next dev` after `next build` (or run them in separate checkouts).
> This caused a transient 13-failure run during this pass; a clean dev restart
> restored 43/43.

## Results by category
- **UNIT / API / SECURITY (pytest):** 261 passed — auth, password reset, admin,
  products, plan, photos, validation, insights, premium features, scoring,
  database, security (JWT/IDOR/rate-limit), profile/progress, glow/arc/glowups.
- **E2E (Chromium):** auth (signup weak/valid/duplicate, login wrong/valid/throttle),
  momentum page loads (/arc /glow /glowups /dashboard), security headers +
  CORS + info-disclosure, 401/route-guard, responsive (16), a11y (4), visual
  capture (4).
- **CROSS-BROWSER:** 9 `@critical` tests × Firefox + WebKit all pass.
- **RESPONSIVE:** no horizontal overflow on landing/login at all 8 viewports.
- **VISUAL:** 7 full-page screenshots captured (`TESTING/screenshots/`).
- **ACCESSIBILITY:** axe 0 critical/serious on login, signup, dashboard;
  password toggle keyboard-operable.
- **SECURITY:** hardening headers on 200/401/429, CORS allow-list, no password
  hash leakage, login throttle (10→429), rate limiting.
- **PERFORMANCE:** page loads observed < 5s local (Next dev); `/health` < 500ms.
  No dedicated load test (k6 not installed).

## Findings (see DEFECTS.md for detail)
- **P0 (critical):** none.
- **P1 (high):** none.
- **P2 (medium):** DEF-001 a11y link contrast (FIXED); DEF-004 postcss/next
  dependency advisories via npm audit (FIXED — non-breaking npm `overrides`).
- **P3 (low):** DEF-002 health memory metric (FIXED); DEF-005 deprecation
  warnings (OPEN); DEF-006 in-memory rate limit/login throttle (OPEN, pre-existing).

## NOT TESTED (explicit)
- Upload → Cloudinary → analysis → results (needs real image upload / Cloudinary).
- Stripe payments success path — **now covered** (see “Payments lifecycle pass”
  below). The honest-fail 503 path (no keys) remains covered by backend tests.
- pip-audit (venv has no pip), OWASP ZAP DAST, CodeQL, k6 load, screen-reader
  pass, interactive Playwright MCP exploration.

## Release status
**READY WITH ACCEPTED RISKS** for the current local/staging state. Core
functionality, authentication, authorization gating, security headers, momentum
features, and the browser matrix all pass. Before a production deploy, complete
the deploy gates in `RELEASE-CHECKLIST.md` (set SECRET_KEY / CORS / FRONTEND_URL
in Render, plus Stripe, Cloudinary, SMTP, Redis — code-side hardening is done).
## Payments lifecycle pass (API-only, no UI/browser)

- **Date:** 2026-09-16
- **Environment:** macOS, Python 3.12 venv, local SQLite (`lookmaxx.db`), backend on
  `127.0.0.1:8000`, **real Stripe test mode** (`stripe` lib 15.6.1, account API
  `2026-08-26.dahlia`).
- **Method:** `backend/scripts/payments_e2e.py` drives the real Stripe test account
  through `POST /payments/checkout` → completes the session → replays the resulting
  events as **signed** webhooks (`stripe-signature`, test `STRIPE_WEBHOOK_SECRET`)
  to the local endpoint, then asserts app state via `/auth/me` and `/entitlements`.
  No browser involved.

| Suite | Passed | Failed |
|---|---|---|
| `scripts/payments_e2e.py` (8 scenarios, 52 assertions) | 52 | 0 |
| Backend pytest (full) | 295 | 0 |
| Frontend `tsc --noEmit` | clean | — |
| Frontend `next build` | clean | — |

**Scenarios covered (all pass):** Free→Pro monthly (£1 first-month offer + coupon,
offer flagged used), Pro→Elite annual upgrade (expiry extends ~365d), Elite→Pro
annual downgrade, cancel-at-period-end (access persists, flag set), resume (flag
cleared), cancel-immediately (revoked → free), re-subscribe after cancellation,
forced end-of-period expiry (expired Pro reads as `free` everywhere and loses
unlimited analyses).

**Tests corrected:** `tests/test_premium_gating.py` — three assertions were stale
against the current build: checkout/webhook “unconfigured” 503 checks now
`monkeypatch` the setting to empty (keys are present in `.env`), and the removed
test-upgrade endpoint is now asserted to 404 instead of 403.

**Production note (`DEF-009`):** real *local* checkouts are charged by Stripe but
their webhooks are delivered to the Render endpoint, so local app state does not
update. Forward with `stripe listen --forward-to
http://127.0.0.1:8000/api/v1/payments/webhook` (and use its `whsec_…`), or
reconcile an affected user with `scripts/stripe_sync.py <email|customer_id>`.

## Mobile account drawer regression pass (2026-09-16)

**Report:** on a phone viewport, tapping the avatar (top-right) opened only the
drawer's header (name / email / ✕) — Profile, Settings, Upgrade and Log out were
missing. Desktop was unaffected.

**Root cause (DEF-010):** `AvatarDrawer` was rendered *inside* the sticky
`<header>`. `backdrop-blur` on that header is a `backdrop-filter`, which makes the
element the containing block for `position: fixed` descendants, so the drawer's
`fixed inset-0` overlay resolved against the 64px header box; `overflow-hidden`
then clipped every row, and the header's `z-40` stacking context trapped the
overlay beneath the bottom tab bar. Measured on the pre-fix build at 390×844:
overlay height **64px** (viewport 844px), rows laid out at y≈72–200, and
`elementFromPoint` at each row centre returned page content, i.e. nothing was
tappable. The desktop path was never affected because the drawer is `md:hidden`.

**Fix:** `TopNav` returns a fragment containing `<header>` and `<AvatarDrawer>`
as **siblings** (with a comment explaining why it must stay outside), plus
safe-area bottom padding and a scrollable menu. No API, data or desktop-nav
change.

**Verification:** `e2e/account-drawer.spec.ts` (5 tests, new).

| Run | Target | Result |
|---|---|---|
| Green | fixed source, isolated dev build (390×844) | **5/5 passed** |
| Red | pre-fix production build still served on `localhost:3000` | **4/5 failed** (clipping + both tap tests + z-order) |

- `tsc --noEmit`: clean after the change.
- `next build` (isolated checkout, so the running local server is untouched): clean.
- The pre-existing full-suite totals above (43 Chromium / 18 cross-browser)
  predate this spec; a full Chromium run is now 48 tests. The rest of the suite
  was **not** re-run in this pass.
- Environment note while verifying: repeated signup/login calls from the runner
  tripped the backend's anonymous rate limit (60/min per IP, DEF-003 family) —
  expected behaviour, not a defect. The `:3000` server was serving a stale
  production build, so the fix only appears there after a rebuild.

## Symmetry + first-month price pass (2026-09-16, DEF-014 / DEF-015)

Two production-reported bugs: **"Symmetry 0"** on a real face, and **£1 charged
while the UI said £9.99**.

### DEF-014 — Symmetry 0 (root cause, then fix)

Reproduced on the pre-fix code in one command:

```
detect_face_landmarks(jpeg) → success=True mock=True n=468
calculate_symmetry(mock)   → 0        ← exactly the production value
calculate_jawline_score    → 42.9     ← production showed 43
calculate_eye_score        → 37.4     ← production showed 37
```

So the row was produced by **synthetic ellipse landmarks**, not by a broken
symmetry formula: `/photos/analyze/{id}` (the endpoint the web upload flow calls)
checked only `success`, and `detect_face_landmarks` returned `success: true` +
468 fabricated landmarks whenever MediaPipe was unavailable. The ellipse's mirror
pairs are not mirrored, so `100 − dist × 250` clamped to exactly 0, while
jawline/eyes landed in plausible ranges — which is why only symmetry looked broken.

| Check | Result |
|---|---|
| Unavailable detection now returns `success: false`, `landmarks: []`, a reason | ✅ (never synthetic geometry) |
| Old mock ellipse → `calculate_symmetry` | ✅ `None` (documents that it used to be exactly 0) |
| Missing / degenerate landmarks → `None`, not 0 or the old 70.0 default | ✅ |
| Realistic landmark set → 70–100 | ✅ |
| `POST /photos/analyze/{id}` with a non-measured result | ✅ 422, `analysis_status="failed"`, **no** scores written, **no** plan row |
| `POST /photos/analyze/{id}` with real landmarks | ✅ 200, symmetry > 0, `analysis_details.landmark_measurement="measured"` |
| `GET /analysis/{id}` with a stored `symmetry_score = 0` | ✅ returns `symmetry: null` + `measurement.not_measured: ["symmetry"]` |
| `GET /analysis/{id}` when landmarks were unavailable | ✅ does **not** borrow heuristic category estimates |
| Legacy repair on boot (`symmetry_score <= 1`, others `<= 0` → NULL) | ✅ ran against the dev DB: "Repaired 4 impossible legacy score(s)" |
| `GET /health` | ✅ now reports `mediapipe: {available, model_path, model_path_exists, reason}` |
| Results UI for an unmeasured row | ✅ "—" + tooltip + a one-line explainer (Playwright, stubbed payload) |

### DEF-015 — £1 first month invisible (root cause, then fix)

The backend was already correct (production OpenAPI confirms `CheckoutIn.first_month_offer`
and `has_used_first_month_offer` in `UserResponse`; Stripe test account confirms
coupon `FIRST_MONTH_1`, `amount_off 899 gbp`, `duration once`, Pro monthly `999 gbp`).
The break was presentation: a detached £1 banner above a Pro card headlining
£9.99/mo, hardcoded copy, and **no confirmation page at all**
(`success_url` → `/dashboard?upgraded=1`, which no frontend code handled — 0 hits).

| Check | Result |
|---|---|
| `GET /payments/offer`, eligible free user (live Stripe test mode) | ✅ `eligible: true, first_month_amount: 1.0, regular_amount: 9.99, source: "stripe", verified: true` |
| Same endpoint, offer already used / already subscribed / no coupon id | ✅ `reason: used` / `already_subscribed` / `not_configured`, `eligible: false` |
| Stripe unreachable | ✅ 200 with `source: "config"`, `verified: false` (never a 5xx on the pricing page) |
| `POST /payments/checkout` with `first_month_offer: true` (live test mode) | ✅ session created; Stripe reports `amount_total=100`, `total_details.amount_discount=899`, `discounts[0].coupon=FIRST_MONTH_1` |
| `GET /payments/checkout/{session_id}` (live test mode) | ✅ 200 → `amount_charged: 1.0, amount_discount: 8.99, first_month_offer: true` — exactly what the success page prints |
| Same endpoint, another user's session / unknown session | ✅ 404 both (ownership checked against `client_reference_id` + metadata) |
| Upgrade page, eligible (`/payments/offer` stubbed) | ✅ Pro card headlines £1.00, struck-through £9.99, "Then £9.99/month from month 2", CTA "Start for £1.00" |
| Upgrade page, annual view (the default) | ✅ still surfaces "Prefer £1.00 for your first month? Switch to monthly" (the first version of the fix hid this — caught by the test) |
| Upgrade page, offer used / not configured | ✅ no £1 claim anywhere; list price + "Your £1 first month has already been used." |
| `/upgrade/success` for a £1 charge | ✅ "You were charged £1.00 for your first month.", discount −£8.99, next payment £9.99/mo on 16 October 2026 |
| `/upgrade/success` for a full-price charge | ✅ "You were charged £9.99", no offer claim, no discount row |

**Bug found by the live run (not by unit tests):** `metadata.get(...)` on a real
`StripeObject` raises *"'get' is a dict method, but a StripeObject is not a dict"*
→ the new receipt endpoint returned **500** until fixed. The unit stubs now use
attribute-only objects (no `.get`) so this cannot regress.

### Totals

| Suite | Result |
|---|---|
| Backend `pytest` | **325 passed** (295 before; +30 new: 15 symmetry/background + 15 payments/offer/receipt) |
| `e2e/score-clarity.spec.ts` (new) | **9 passed** |
| `e2e/tier-clarity.spec.ts` | **5 passed** (the `/glow-up` + `/peak-you` rows are analysis-dependent; their locked state is now asserted deterministically in `score-clarity.spec.ts`, and the loop documents why) |
| Full Chromium suite | **62 passed, 0 failed** (was 61 with 1 failure before this pass — the failure was `/glow-up`'s analysis-dependent row, now handled) |
| `tsc --noEmit` | clean |

Also hardened while in here: `ai_service` copied scores with
`score_data.get("symmetry_score", 70)`, which returns `None` (not 70) when the key
exists with a `None` value — so `if skin >= 75:` raised `TypeError` on any
unmeasured photo and silently dropped the template analysis. `_copy_score()`
coalesces for wording only; the scored columns stay NULL.

**Post-payment fields** (`paid: true`, next-payment date) are covered by the
payments unit tests with attribute-only Stripe stubs: this Stripe account/API
version does not expose `POST /v1/checkout/sessions/{id}/confirm`, so a test-mode
checkout cannot be completed programmatically. Everything up to and including the
amount Stripe will charge was verified against the live test API.

## Pro vs Elite matrix audit (2026-09-16)

**Scope:** every menu and every page, as free / Pro / Elite, asking two questions:
*which* plan unlocks this, and can the user get there without guessing?

**Method:** a HEAD backend was booted on `127.0.0.1:8001` against a throwaway
SQLite DB (`/tmp/lm-audit-head.db`) — the long-running local `:8000` was a stale
build whose `/entitlements` still listed a phantom Elite perk, so it was not used
for evidence. Three users were created (free, then `subscription_tier` flipped to
`pro`/`elite` in that throwaway DB) and every gated endpoint was probed with each
token; the UI was then walked page-by-page at 1280×900 and 375×812.

### Endpoint gates (what is *really* enforced)

| Endpoint | Free | Pro | Elite |
|---|---|---|---|
| `GET /coach` | 403 | 200 | 200 |
| `GET /analysis/{id}/report`, `/insights` | 403 | 200 | 200 |
| `POST /arc/quests/{id}/claim` | 403 | 200 | 200 |
| `GET /glow/full-reveal` | 403 | **403** | 200 |
| `GET /glowups/movie` | 403 | **403** | 200 |
| `GET /plan`, `GET /progress/*`, `GET /arc/state`, `GET /arc/badges`, `GET /products/*` | 200 | 200 | 200 |

The last row is the DEF-012 finding: four features sold as Pro perks are free
today, so tier labelling (not gating) was corrected this pass.

### Page-by-page result after the fix (free member)

| Surface | What a free member now sees |
|---|---|
| Primary nav (desktop + mobile) | `Coach` carries a padlock, accessible name "Coach Pro"; Home/Plan/Glow/Explore carry nothing |
| Glow sub-nav | `Insights` and `Simulator` carry a "Pro" chip; `Daily` and `Journey` do not |
| Dashboard | "Pro unlocks" and "Elite only" groups, each row chipped, CTA "See Pro & Elite" |
| /coach, /glow-up, /peak-you, /upload | `PaywallLock` naming the exact plan ("Upgrade to Pro" / "Upgrade to Elite") |
| /arc | "Upgrade to Pro" beside the quest lock (previously a dead end) |
| /glowups | "Upgrade to Elite" in the movie card (previously a dead end) |
| /explore | Glow-Ups card carries an Elite chip and says the browse feed is free |
| /glow, /plan, /products, /progress, /settings, /upgrade | No false tier claims (see DEF-012 for the copy that was removed) |

### Evidence

| Check | Result |
|---|---|
| `e2e/tier-clarity.spec.ts` (new, 5 tests) | **5/5 passed** |
| `e2e/account-drawer.spec.ts` (regression after the nav edit) | **5/5 passed** |
| `tsc --noEmit` | clean |
| `next build` (isolated checkout) | clean |
| Pro tier sees Elite CTAs, Elite tier sees none | verified per page (dashboard/glow-ups/glow-up/arc/peak-you) |
| 375px tab bar with the Coach padlock | 5 tabs, equal width, no horizontal overflow |

**Not re-run:** the full Chromium/Firefox/WebKit suites (the local `:3000` server
is a stale production build and its `:8000` API a stale checkout; both need a
restart before a whole-suite pass). New totals would be 53 Chromium tests.

## £1 offer visibility pass (2026-09-17, DEF-016)

**Report:** "the £1 first-month coupon is missing for new users — it shows the full
price instead" (local `:3000` → Render API).

### What the API actually said (live, brand-new free account)

Reproduced against production with an account created minutes earlier
(`cline-verify-20260917@mailinator.com`):

| Call | Result |
|---|---|
| `GET /payments/offer` | `eligible: true`, `reason: "eligible"`, `source: "stripe"`, `verified: true`, `first_month_amount: 1.0` (100 minor), `regular_amount: 9.99` (999 minor) |
| `GET /auth/me` | `subscription_tier: "free"`, `is_subscribed: false`, `has_used_first_month_offer: false` |
| `POST /payments/checkout {tier: "pro", annual: false, first_month_offer: true}` | `cs_test_…` → `GET /payments/checkout/{id}`: `amount_charged: 1.0`, `amount_discount: 8.99`, `first_month_offer: true` |

So the coupon **`FIRST_MONTH_1` is live in the deployed Stripe account and is being
honoured** (£8.99 off a £999 price = £1.00 charged), eligibility is **per account**
(two abandoned, unpaid test sessions did *not* consume it — the flag is only set on
`checkout.session.completed`, `payments.py:651`), and the server-side guard
(`payments.py:349`) refuses the coupon to anyone who has used it. **Nothing on the
backend was wrong**, and no env var needs changing for this to work.

### Root cause

`/upgrade` opened on the **annual** view (`useState(true)`), while the coupon is
`duration=once` on the Pro **monthly** price. An eligible new member's first paint
was therefore the annual card — £4.20/mo headline, £9.99/mo struck through, CTA
"Start Pro" — with the £1 offer demoted to a small underlined link beneath it. The
£1 *was* reachable (clicking **Monthly** rendered £1.00 correctly), but the default
state that a new user actually lands on advertised list price.

The existing tests missed it because all three offer tests clicked **Monthly** first:
they asserted a view the tester had to go and find.

### Fix + evidence

| Check | Result |
|---|---|
| Landing `/upgrade` as an eligible free member, **zero interaction** | **£1.00 first month**, £9.99 struck, "Then £9.99/month from month 2 · cancel anytime", CTA **"Start for £1.00"** |
| Choosing *Annual* yourself | annual figures (£50.40/yr) plus a visible gold button "Switch to monthly for a £1.00 first month"; the manual choice is **not** reverted when eligibility resolves later |
| While `/payments/offer` is in flight | the Pro card reads "Checking your price…" — £9.99 is never printed and then replaced |
| `e2e/score-clarity.spec.ts --grep server-authoritative` (Chromium) | **6/6 passed** (landing £1, annual still surfaces it, view choice respected, no price before the answer, used offer, unconfigured) |
| `tsc --noEmit` | clean |

Run note: the offer tests are fully API-stubbed, so they do not need the backend.
This Mac can no longer start the API-driven suite (`../backend/.venv` is gone and
`mediapipe 0.10.21` has no macOS-arm64 wheel), so the 4 offer tests were run with
`reuseExistingServer` and a stand-in server answering `GET /api/v1/health` on
`:8000`; the landing/annual assertions above are live browser runs against Render.

### Go-live note (still yours to do)

Production is on **test-mode** Stripe keys — every session the deployed API creates
is `cs_test_…`, and `FIRST_MONTH_1` exists only in the *test* account. Moving to
live keys without recreating the coupon + prices makes this offer disappear for
real users: `/payments/offer` degrades to `verified: false` and the card falls back
to list pricing.


## £1 offer banner + checkout error-handling pass (2026-09-17, DEF-017)

**Report:** "the coupon on top horizontal format has disappeared" (the £1 offer had
been buried inside the Pro card) **and** "clicking *Start for £1.00*, Stripe checkout
fails".

### Checkout was not broken — the probe was

| Call (live, `https://lookmaxx-api.onrender.com/api/v1`) | Result |
|---|---|
| `POST /payments/checkout {tier: "pro", annual: false, first_month_offer: true}` | **HTTP 200 in 0.79 s**, `checkout_url: https://checkout.stripe.com/c/pay/cs_test_…#fidnandh…` |
| `GET /payments/checkout/{session}` | `status: "open"`, `amount_charged: 1.0` (100 minor), `amount_discount: 8.99` (899 minor), `first_month_offer: true` |
| The hosted page (clean browser context) | "LOOKMAXX · Subscribe to Pro Monthly · **£1.00** · Then £9.99 per month starting next month · Subtotal £9.99 · First Month £1 −£8.99 · **Total due today £1.00**" |

The one failure seen — *"This link is incomplete"* with `CheckoutInitError: apiKey is
not set` in the console — was self-inflicted: the first navigation dropped the URL's
`#fidnandh…` fragment. That fragment is not session data; it decodes
(`base64 → XOR 5`) to the account's checkout config
`{"borderStyle":"default","gv":0,"apiKey":"pk_test_51UDnBm…","fromServer":true,…}`, so a
URL without it carries no publishable key — hence Stripe's message. The same URL that
failed then rendered correctly in a fresh tab, in a fresh context, and in a fresh
context seeded with the identical cookies + localStorage (no service worker and no
cache storage on the origin), i.e. tab state — not auth, CORS, the coupon, or the
`/payments/checkout` contract. **Deployed Stripe is test mode** (`cs_test_…`,
`pk_test_…`), which is why the coupon is honoured today.

### The two real gaps the report exposed

| Gap | Fix |
|---|---|
| `except Exception: raise HTTPException(502)` around `stripe.checkout.Session.create` logged **nothing** — "checkout failed" with no type, code or request id to debug from | `logger.exception(...)` records `type`, `code`, `param`, `request_id`; a rejection that names the coupon/discount is retried **once at list price** and answers `offer_applied: false`. A non-coupon failure is never retried (a dead API key still 502s) |
| An *unverifiable* coupon (`verified: false` — the live-mode trap) still priced quietly | The banner renders only for `eligible && verified`; otherwise the page prints "The £1.00 first-month offer is temporarily unavailable — the plans below are at their regular price" |

### Fix + evidence

| Check | Result |
|---|---|
| `/upgrade` as an eligible free member, **zero interaction** | gold **banner above the cards**: "FIRST MONTH SPECIAL / Get started for £1.00 / …then £9.99/month from month 2", CTA "Start for £1.00" |
| The three cards | Elite £19.99/mo · Pro **£9.99/mo** (billed monthly) · Free £0 — no £1 headline inside a card, no in-card "switch to monthly" button |
| Banner CTA → Stripe (live click-through, localhost → Render) | `cs_test_…` checkout showing **Total due today £1.00**, "First Month £1 −£8.99" |
| Banner CTA request body (asserted in the suite) | `{tier: "pro", annual: false, first_month_offer: true}` — the monthly plan the coupon prices, even for a visitor left on the annual toggle |
| Annual view | banner still present (offer never hidden); Pro card shows £50.40/yr and CTA "Start Pro" — a button promising £1 while buying annual would be the DEF-015 mismatch again |
| Existing Elite subscriber | "You're already on Elite." + **Current plan**, no banner |
| Existing Pro subscriber (stubbed) | **Current plan** on Pro, "Switch to Elite" on Elite, no banner on either |
| `e2e/score-clarity.spec.ts` (Chromium, API-stubbed) | **15/15 passed** (was 11) |
| `backend/tests/test_payments.py::TestCheckoutCouponFallback` | **compiles** (`python3 -m py_compile`); **not runnable on this Mac** — no backend venv and `mediapipe` has no macOS-arm64 wheel |
| `tsc --noEmit` | clean |

Screenshots: `TESTING/screenshots/upgrade-banner-free.png`,
`upgrade-banner-elite-subscriber.png`, `upgrade-stripe-checkout-pound.png` (the Stripe
page the banner CTA opens: "Total due today £1.00").

**Not re-run:** the £1 test charge itself. Stripe's hosted card fields sit in nested
`js.stripe.com` frames behind hCaptcha, which defeated a bounded automation attempt
(the account stayed `free`, `has_used_first_month_offer: false`). The grant path is
covered by
`test_payments.py::TestStripeWebhook::test_checkout_completed_grants_and_consumes_first_month_offer`.

**Design deviations worth flagging:** (1) the CTA pulse is **finite (2 cycles)** — an
endless `transform` animation fails Playwright's "element is stable" click check and
leaves a tap target that never stops moving; the persistent attention comes from the
banner's gold glow; (2) no click **ripple** — this UI has no ripple primitive, and
adding one would introduce an interaction pattern the rest of the app's `Button`s
don't share; (3) the eligible free member still defaults to the **monthly** view
(DEF-016's fix), so the Pro card reads £9.99/mo rather than the annual £4.20/mo while
its CTA states "Start for £1.00" — the price block is the regular price, the button is
the amount charged.


## Paid-but-Free: the webhook refused every event (2026-09-17, DEF-018)

**Report:** "Stripe window shows the payment, but the backend never hits the webhook to
upgrade the UI — payments are failing." In Stripe the catalogue looks healthy (4
products/prices, `First Month £1` = £8.99 off once, **16 redemptions**, Active), so
checkout itself is completing.

**Root cause — reproduced on the live API, not inferred.** `render.yaml` sets
`ENVIRONMENT=production`, and the deployed Stripe keys are **test** keys. The webhook's
sandbox guard read the environment's *name*:

```python
if settings.ENVIRONMENT == "production" and event.get("livemode") is not True:
    raise HTTPException(status_code=400, detail="Test-mode event rejected in production.")
```

Every test-mode event carries `livemode: false`, so **every** delivery was refused —
including perfectly valid, correctly signed ones. The card was charged, the receipt was
rendered from the real session, and the account stayed `free`, with nothing able to
retry or notice.

| Probe (deployed API, pre-fix) | Result |
|---|---|
| `POST /api/v1/payments/webhook` — synthetic `checkout.session.completed`, signed with the deployed `STRIPE_WEBHOOK_SECRET`, `livemode: false`, `metadata.tier=pro` | `400 {"detail":"Test-mode event rejected in production."}` |
| Unsigned `POST …/webhook` (control) | `400 {"detail":"Invalid webhook signature."}` — i.e. **403 ≠ the guard**: the secret *is* configured, so the signed probe above really did pass signature verification and was refused only by the livemode guard |
| `GET /api/v1/auth/me` for that user afterwards | `subscription_tier: "free"`, `is_subscribed: false` |
| `/api/v1/health`, `render.yaml` | healthy; `ENVIRONMENT: production` declared in the blueprint |

**Fix (4 parts).** (a) The guard now keys off the key the deployment authenticates with —
`_deployment_is_live()` returns True only for `sk_live_…` — so a pre-launch production box
on test keys processes its own sandbox traffic, while a live deployment still refuses any
event Stripe did not mark `livemode: true`; rejections are logged with the event id. (b) A
boot-time warning fires whenever production runs sandbox keys (the misconfiguration was
silent before). (c) `GET /payments/checkout/{id}` now **reconciles the grant** from
Stripe's own `payment_status` — owner-checked against `metadata.user_id` /
`client_reference_id`, idempotent through `grant_subscription`, anchored to the
subscription's real period end so a 7-day Elite trial is not recorded as 30 days, and
granted only while that term is still running (revisiting a lapsed receipt must not
resurrect access) — so the upgrade no longer hinges on a single delivery. (d) The success
page invalidates the `me`/`entitlements` queries once the receipt reports `paid`: the top
nav had cached the pre-payment tier and runs with `refetchOnWindowFocus: false`, so a
correct grant still *looked* like "the UI never upgraded".

| Check | Result |
|---|---|
| `backend/tests/test_payments.py` | **49 passed** (was 40; 9 new) |
| New: sandbox event on a production box with test keys | 200 + `tier=pro`, offer consumed |
| New: sandbox event with **live** keys | 400, user stays `free` (protection intact) |
| New: live event with live keys | 200 + `tier=elite` |
| New: reconciliation (6 tests) | paid session grants with no webhook at all; unpaid and abandoned (`status=open`) grant nothing; a 7-day trial end is kept (not 30 days); a **lapsed** subscription's old receipt does not resurrect access (a session stays `paid` forever, so only a still-running term is reconciled); re-reading the receipt neither extends nor double-audits |
| **Regression proof** — the same tests against `7f09640` (pre-fix code) | 4 failed exactly as production did: `400`, `tier=free`, `assert 'free' == 'elite'`, `assert 0 == 1` (no audit row) |
| Full backend suite (`python -m pytest`) | **338 passed** in 92 s |
| `frontend` `tsc --noEmit` | clean |
| `frontend/e2e/score-clarity.spec.ts` (Chromium, API stubbed, re-run after the success-page change) | **15/15 passed** in 26 s — including the two receipt tests that exercise the new cache invalidation |
| Deploy verification (post-fix, same signed sandbox event, against the redeployed API) | **`200 {"success": true}`**, then `GET /auth/me` → `subscription_tier: "pro"`, `is_subscribed: true` — where minutes earlier the identical request returned `400` and left the user `free` |
| Deploy verification, replaying the same `event.id` | `200 {"success": true, "duplicate": true}`, tier unchanged — `stripe_events` idempotency holds in production |

**Backend tests are now runnable on this Mac (new).** The blocker was never the code: no
venv existed and the pinned `mediapipe==0.10.21` has no wheel for Python 3.14/arm64. Its
imports (like torch's) are lazy, so a throwaway venv without them runs the whole suite:

```bash
python3 -m venv /tmp/lmvenv
/tmp/lmvenv/bin/pip install fastapi sqlalchemy stripe pytest httpx pydantic-settings \
  'python-jose[cryptography]' 'passlib[bcrypt]' \
  bcrypt==4.0.1 python-multipart python-dotenv email-validator \
  cloudinary redis openai numpy Pillow opencv-python   # bcrypt must be <4.1 for passlib 1.7.4
cd backend && /tmp/lmvenv/bin/python -m pytest -q
```

**For the dashboard (what to check for the 16 redemptions that were charged but not
granted):** Developers → Webhooks → the endpoint → *Recent deliveries* should show the old
attempts with a `400 Test-mode event rejected in production.` body — after this deploy,
hit **Resend** on those events and each one grants, because the grant path is idempotent
(`{"duplicate": true}` on a second delivery). If a delivery instead reports
`Invalid webhook signature`, the `whsec_…` on Render belongs to a different endpoint; if
there are no deliveries at all, the endpoint is not subscribed to
`checkout.session.completed`.

**Cards, in test mode:** only Stripe's test cards can be charged (`4242 4242 4242 4242`,
any future expiry, any CVC/postcode; `4000 0000 0000 0002` always declines, and
`4000 0025 0000 3155` forces 3-D Secure). A real card in test mode is expected to fail —
that is the usual "the Stripe window won't take my payment" report, and it is unrelated to
the webhook defect above.

**When the launch switches to live keys (next step), the guard switches on with them.**
`sk_live_…` makes the webhook refuse anything Stripe did not mark `livemode: true`, which
is the point — but the live-mode endpoint has a **different** `whsec_…` than the test one,
so `STRIPE_WEBHOOK_SECRET` must be replaced in the same deploy as `STRIPE_SECRET_KEY`, and
the four `STRIPE_PRICE_*` ids plus the `FIRST_MONTH_1` coupon must be recreated in live
mode (test-mode ids do not exist there). Symptoms if that is done piecemeal: `Invalid
webhook signature` (secret still from test mode) or `No such price`/`No such coupon`
(ids still from test mode — checkout then 502s, or falls back to list price with
`offer_applied: false`). `GET /payments/offer` returning `verified: true` is the cheapest
end-to-end check that the live coupon is reachable.

