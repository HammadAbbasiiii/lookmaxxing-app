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

