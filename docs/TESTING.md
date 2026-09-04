# Testing — LookMaxx

A "brutal tester" pass over the whole app. This document records what is
covered, how to run it, and every issue the test pass uncovered (and fixed).

## Run

```bash
# Backend (FastAPI + pytest) — the authoritative test suite
cd backend
.venv/bin/python -m pytest            # or: pytest

# Frontend type safety (no runtime UI tests yet)
cd frontend
npm run typecheck                     # tsc --noEmit
```

> The backend suite runs against a throwaway SQLite DB (`backend/test_lookmaxx.db`)
> via a `get_db` dependency override — it never touches the live Postgres DB.

## Current result

```
187 passed, 437 warnings in ~46s
```

## Test files & coverage

| File | What it proves |
|---|---|
| `tests/test_auth.py` | Password hashing, JWT creation, signup/login/me, duplicate email, email trimming, wrong password, invalid/missing token. |
| `tests/test_password_reset.py` | **NEW** — forgot-password (anti-enumeration 200 for known/unknown email, hashed token storage, prior-token invalidation), reset (valid → login, single-use replay 400, forged/expired 400, short password 422), `verify`, session revocation on reset, per-email throttle → 429. |
| `tests/test_admin.py` | Admin user list, promote/demote (+audit), idempotency, self-demote blocked, tier override (pro/elite/free, case-insensitive, invalid). |
| `tests/test_admin_products.py` | **NEW** — product CRUD (create/update/archive/activate), category/tier/price/rating validation, search/filter, audit log, `/track`, `/admin/overview|events|funnel|retention|events/summary` + 403 gates. |
| `tests/test_plan.py` | Plan check-in JSON body, empty tasks, check-in without active plan. |
| `tests/test_photos.py` | Photo upload auth, invalid file type, upload success, list photos. |
| `tests/test_validation.py` | Image pre-validation (too small/dark/bright, low contrast, blurry). |
| `tests/test_insights.py` | Pro/Elite insights gating + payload shape, forecast/rank/archetype/blueprint determinism. |
| `tests/test_premium_features.py` | Nested `category_breakdown` regression for coach/report/insights/harmony/recommendations + `_anonymize`. |
| `tests/test_scoring_calibration.py` | Score calibration. |
| `tests/test_database.py` | DB layer. |
| `tests/test_security.py` | **NEW** — password/email validation, email normalization, secret non-leakage, JWT tampering/expiry/wrong-key/`alg=none`/malformed/empty, **IDOR** (cross-user photo/report access → 404), **rate limiting** (anonymous + per-user buckets), ADMIN_EMAILS fallback. |
| `tests/test_profile_progress.py` | **NEW** — profile GET/PUT + field validation, onboarding, GDPR delete (token orphaned → 401), progress endpoints, **streak engine** (first/consecutive/gap/idempotent/tie-break), check-in once-per-day (409). |
| `tests/test_premium_gating.py` | **NEW** — freemium limits (1 free analysis/photo), entitlements (free/pro/elite), coach gating (free 403, pro 200), payments (checkout 503 unconfigured, invalid tier 422, test-upgrade 403, webhook 503). |
| `tests/test_plan_dashboard_products_explore.py` | **NEW** — plan, dashboard, product browse (categories/category/recommendations + validation), explore, analysis (scored/unscored/missing/IDOR), health/root, upload signature. |

## Security guarantees locked in by tests

- **No password hashes in any response** (signup, `/me`, admin user list).
- **IDOR blocked** — user A cannot read user B's photo/report (`404`, not `403`).
- **JWT hardening** — tampered, expired, wrong-key, `alg=none`, malformed and empty tokens all `401`.
- **Password reset** — anti-enumeration (identical 200 for known/unknown email), single-use hashed token, 30-min expiry, per-email throttle, and session revocation (`token_version` bump) on reset.
- **Rate limiting is per-identity** — anonymous bucket (60/min) and authenticated bucket (200/min, keyed on the JWT `sub`).
- **Freemium is server-authoritative** — free tier is hard-capped at 1 analysis/photo via `enforce_analysis_limit` / `enforce_photo_limit`.
- **Premium gating is per-endpoint** — coach/report/insights need Pro, harmony needs Elite; the 403 carries a machine-readable `code: "upgrade_required"`.
- **Admin is email-OR-flag** — `require_admin` honours both the `is_admin` flag and `ADMIN_EMAILS`.
- **Email normalization** — case/whitespace variants dedupe to one account.

## Issues found & fixed by this pass

1. **Rate limiter never keyed on the user** (`app/middleware/rate_limit.py`).
   `request.state.user_id` was read but *never set anywhere*, so **every** request
   (authenticated or not) was bucketed as `"anonymous"`. The `AUTHENTICATED_LIMIT`
   was dead code and a single shared 60/min bucket applied to all traffic.
   **Fix:** middleware now decodes the bearer JWT to derive `user:{sub}`, falling
   back to `"anonymous"` only when the token is missing/invalid.

2. **`GET /products/category/{cat}` and `GET /products/categories` returned 500**
   (`app/routes/products.py`). Both called `get_products_by_category(...)/get_categories(...)`
   with `db=db` but never declared a `db` dependency → `NameError`.
   **Fix:** added `db: Session = Depends(get_db)` to both routes.

3. **Product recommendation sort crashed on `rating = None`**
   (`app/services/product_recommendation_service.py`). `_sort_key_rating` did
   `product.get("rating", 0) * log(...)`, which is `None * float` → `TypeError`
   as soon as any product (e.g. an admin-created product without a rating) was in
   the catalogue.
   **Fix:** coerce `rating`/`reviews_count` with `or 0` before the arithmetic.

## Known remaining gaps (honest notes)

- **Frontend has no runtime UI test runner** (no Vitest/Playwright yet). Frontend
  coverage today is `tsc --noEmit` type safety + the backend contract tests that
  mirror every UI action. Adding Vitest + Testing Library / Playwright E2E is the
  recommended next step (login→upload→results→admin flows).
- **Deprecation warnings** (`datetime.utcnow()`, Pydantic class-config) are
  cosmetic and non-blocking; migrate to timezone-aware datetimes / `ConfigDict`
  opportunistically.
- `ALLOW_TEST_PAYMENTS`/Stripe paths are verified for their **honest failure**
  (503/403) behaviour; a real checkout requires live Stripe keys.
