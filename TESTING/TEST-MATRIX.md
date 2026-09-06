# Test Matrix — LookMaxx

> Phase 3 deliverable. Maps each important requirement/behavior to at least one
> test. Type: U=unit, I=integration, A=API, C=contract, E=E2E, UI=UI, V=visual,
> AX=accessibility, S=security, P=performance, R=responsive, X=cross-browser, RG=regression.

Status legend: ✅ implemented · ⬜ planned this pass.

## 1. Authentication (CRITICAL)

| ID | Description | Type | Expected | Status | File |
|---|---|---|---|---|---|
| AUTH-01 | Valid signup | A,E | 200, UserResponse, no hash | ✅ | backend/tests/test_auth.py, e2e/auth.spec.ts |
| AUTH-02 | Missing fields | A | 422 | ✅ | test_auth.py |
| AUTH-03 | Invalid/malformed email | A,E | 422 | ✅ | test_auth.py, test_security.py |
| AUTH-04 | Weak password (common/short/single-class) | A,E,UI | 422 + strength meter | ✅ | test_password_strength.py, e2e/auth.spec.ts |
| AUTH-05 | Email-as-password rejected | A | 422 | ✅ | test_password_strength.py |
| AUTH-06 | Duplicate account (case/whitespace) | A | 409/400, dedupes | ✅ | test_auth.py |
| AUTH-07 | Password not stripped | A | leading/trailing spaces preserved | ✅ | test_auth.py |
| AUTH-08 | Valid login | A,E | 200 + JWT | ✅ | test_auth.py, e2e/auth.spec.ts |
| AUTH-09 | Wrong password / unknown email | A,E | 401 (anti-enumeration) | ✅ | test_auth.py, e2e/auth.spec.ts |
| AUTH-10 | Login throttle (10/15min per email+IP) | A | 429 after N failures | ✅ | test_security.py |
| AUTH-11 | JWT tamper/expiry/wrong-key/alg=none/malformed/empty | A | 401 | ✅ | test_security.py |
| AUTH-12 | Session revocation on reset (token_version) | A | old token 401 | ✅ | test_password_reset.py |
| AUTH-13 | Forgot/reset: anti-enumeration, single-use, expiry, throttle | A | 200/400/422 as spec'd | ✅ | test_password_reset.py |
| AUTH-14 | Protected route redirects anonymous | E | → /login?next=… | ⬜ | e2e/unauthorized.spec.ts |
| AUTH-15 | 401 clears token + redirect | E | friendly msg, no crash | ⬜ | e2e/unauthorized.spec.ts |

## 2. Authorization (CRITICAL)

| ID | Description | Type | Expected | Status | File |
|---|---|---|---|---|---|
| AUTHZ-01 | Free tier blocked from Pro endpoints | A | 403 code=upgrade_required | ✅ | test_premium_gating.py |
| AUTHZ-02 | Pro allowed on Pro endpoints | A | 200 | ✅ | test_premium_gating.py |
| AUTHZ-03 | Elite-only endpoints (harmony, glow full-reveal, glowups movie) | A | 403 for pro | ✅ | test_premium_gating.py, test_glow.py, test_glowups.py |
| AUTHZ-04 | Admin gate (non-admin → 403) | A | 403 | ✅ | test_admin.py, test_admin_products.py |
| AUTHZ-05 | IDOR: user A cannot read user B photo/report | A | 404 | ✅ | test_security.py, test_plan_dashboard_products_explore.py |
| AUTHZ-06 | Arc quest claim is Pro-gated | A | 403 for free | ✅ | test_arc.py |
| AUTHZ-07 | Admin UI redirects non-admin | E | redirect/guard | ⬜ | e2e/unauthorized.spec.ts |

## 3. Core app flows (HIGH)

| ID | Description | Type | Expected | Status | File |
|---|---|---|---|---|---|
| FLOW-01 | Upload → analyzing → results | E | score reveal | ⬜ | e2e (future; needs Cloudinary) |
| FLOW-02 | Check-in → streak increments | A | 200/409 | ✅ | test_profile_progress.py |
| FLOW-03 | Dashboard renders aggregate | A | 200 schema | ✅ | test_plan_dashboard_products_explore.py |
| FLOW-04 | Explore anonymizes (no raw URLs) | A,E | no raw face URLs | ✅ | test_plan_dashboard_products_explore.py |
| FLOW-05 | Plan generation | A | 200 + milestones | ✅ | test_plan.py |
| FLOW-06 | Product browse/recs | A | 200, validation | ✅ | test_admin_products.py, test_plan_dashboard_products_explore.py |
| FLOW-07 | GDPR account deletion | A | 200 + token orphaned | ✅ | test_profile_progress.py |

## 4. Momentum engine (HIGH)

| ID | Description | Type | Expected | Status | File |
|---|---|---|---|---|---|
| MOM-01 | Glow state/open/reveals (one/day idempotent) | A | 200, idempotent | ✅ | test_glow.py |
| MOM-02 | Arc state/quests/badges/claim (XP idempotent) | A | 200, no double XP | ✅ | test_arc.py |
| MOM-03 | Glow-Ups feed/consent/movie/report | A | 200, opt-in only | ✅ | test_glowups.py |
| MOM-04 | /arc /glow /glowups pages load (authed) | E | 200, no console errors | ⬜ | e2e/pages.spec.ts |

## 5. Security (CRITICAL)

| ID | Description | Type | Expected | Status | File |
|---|---|---|---|---|---|
| SEC-01 | Security headers on all responses (incl. 429/500) | A,S | X-Content-Type-Options, X-Frame-Options… | ⬜ | e2e/security-headers.spec.ts (+ test_security.py) |
| SEC-02 | No password hash in any response | A | absent | ✅ | test_security.py, test_admin.py |
| SEC-03 | CORS explicit allow-list | A,S | non-listed origin rejected | ⬜ | e2e/security-headers.spec.ts |
| SEC-04 | Rate limiting (anon 60/min, authed 200/min) | A | 429 + Retry-After | ✅ | test_security.py |
| SEC-05 | Error handling leaks no stack | A | generic 500 | ✅ | (error_handler) |
| SEC-06 | Dependency audit (npm/pip) | S | no high vulns | ⬜ | this pass |
| SEC-07 | Secret non-leakage in logs/responses | A | absent | ✅ | test_security.py |

## 6. Accessibility / Responsive / Cross-browser / Visual / Perf

| ID | Description | Type | Expected | Status | File |
|---|---|---|---|---|---|
| AX-01 | axe scan: login/signup/dashboard | AX | 0 critical violations | ⬜ | e2e/accessibility.spec.ts |
| AX-02 | Keyboard: password toggle, form submit | E | operable | ⬜ | e2e/accessibility.spec.ts |
| R-01 | Viewport matrix (8 sizes) no horizontal overflow | R | no h-overflow | ⬜ | e2e/responsive.spec.ts |
| X-01 | Critical suite on Chromium/Firefox/WebKit | X | pass | ⬜ | playwright.config.ts projects |
| V-01 | Screenshot baselines (login/signup/dashboard) | V | stable | ⬜ | e2e/visual.spec.ts |
| P-01 | Page load + API latency baseline | P | reasonable thresholds | ⬜ | documented (no k6 installed) |
