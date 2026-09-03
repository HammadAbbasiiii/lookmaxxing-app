# LookMaxx — Premium Entitlements & Conversion System

> Status: ✅ implemented (backend + frontend)
> Companion to `PRODUCT_SPEC.md` §5 (gating) + `PSYCHOLOGY.md` §5 (freemium).
> New code: `backend/app/services/entitlements_service.py`, `backend/app/routes/{entitlements,coach,payments}.py`, `frontend/src/components/ui/PaywallLock.tsx`, `frontend/src/hooks/useEntitlements.ts`, `frontend/src/app/(app)/coach/`.

## 1. The rule

- The browser is untrusted. Every premium endpoint independently calls
  `require_pro` / `require_elite` in `app/dependencies.py`. The `/entitlements`
  endpoint only feeds *UX* (lock chips + teasers) — it never unlocks data.
- A 403 from the gate carries `detail = {"code": "upgrade_required", "message": ...}`
  so the client can tell an "upgrade required" 403 from any other 403.

## 2. Tiers

| Tier | Analyses | Plan + check-ins | Full report | Daily coach | Before/after | 1:1 coach Q&A |
|---|---|---|---|---|---|---|
| Free | 1 (`FREE_ANALYSIS_LIMIT`) | teaser only | locked | locked | locked | locked |
| Pro | unlimited | ✅ | ✅ | ✅ | ✅ | — |
| Elite | unlimited | ✅ | ✅ | ✅ | ✅ | ✅ |

The feature matrix lives in `app/services/entitlements_service.py` (`FEATURES`) —
one source of truth for both the backend gate and the frontend lock chips.

## 3. Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/entitlements` | ✅ | tier, limits (used/allowed/remaining), feature matrix with `locked` flags |
| GET | `/coach` | Pro | daily AI tip (DeepSeek cached by user+date, template fallback) |
| GET | `/analysis/{photo_id}/report` | Pro | full written report (breakdown, weakest/strongest, recommendations) |
| POST | `/payments/checkout` | ✅ | Stripe Checkout session → `{checkout_url}` |
| POST | `/payments/webhook` | ❌ (signed) | Stripe webhook → grants subscription + audit row |
| POST | `/payments/test-upgrade` | ✅ | dev-only flip (requires `ALLOW_TEST_PAYMENTS=1` AND `ENVIRONMENT != production`) |

## 4. Freemium enforcement

- `enforce_photo_limit` — blocks free users from saving more than
  `FREE_ANALYSIS_LIMIT` photos (called at the start of `/upload/save` and the
  legacy multipart `/photos/upload`).
- `enforce_analysis_limit` — defense-in-depth at `/photos/analyze/{id}`; blocks
  free users with ≥ limit scored photos. Pro/Elite are unlimited.

## 5. Honesty rule (payments)

We never fake a charge:
- Production checkout requires a real `STRIPE_SECRET_KEY` + price IDs. Missing →
  503 `{code: "payments_unconfigured"}` and the frontend shows the waitlist.
- `test-upgrade` refuses to run in production and anywhere without
  `ALLOW_TEST_PAYMENTS=1`.

## 6. Frontend "trap" UX (curiosity at every point)

- `PaywallLock` component — blurred teaser + 🔒 + "Upgrade to Pro".
- Dashboard `ProPerks` — lists the first 3 locked perks with their teasers.
- Results — free users see a locked "Full report" card after the free breakdown.
- Upload — free users who hit the 1-analysis limit see the paywall *before* uploading.
- `/coach` — Pro page; free users see the locked state with the teaser.
- Onboarding (5 steps) + Settings now collect age, gender, goal, skin type,
  skin concerns, and commitment — the data that makes Pro recommendations feel
  personal.

## 7. Data collected from users

`User` now stores `skin_type`, `skin_concerns`, `commitment` (migrated
automatically in `main.py`), plus the pre-existing age/gender/goals/height/weight.
All inputs are server-validated (gender/goals/skin/commitment enums, age 13–120,
height 100–250, weight 30–300).

## 8. Env vars

- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_PRO_MONTHLY/ANNUAL`, `STRIPE_PRICE_ELITE_MONTHLY/ANNUAL`
- `ALLOW_TEST_PAYMENTS=1`, `ENVIRONMENT=production`
- `FREE_ANALYSIS_LIMIT=1`, `FRONTEND_URL=http://localhost:3000`
