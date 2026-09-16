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
