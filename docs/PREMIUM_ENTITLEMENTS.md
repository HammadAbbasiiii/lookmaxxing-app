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

## 2. Tiers — the shipped matrix

Source of truth: `app/services/entitlements_service.py` (`FEATURES`) — the same list
`GET /entitlements` serves and the same one every lock chip in the client reads.
A row is **enforced** only when an endpoint actually refuses a lower tier; a row
that is not enforced is a *free* feature today, whatever the pricing page says.
Verified against HEAD on 2026-09-16 by probing every endpoint with free / Pro /
Elite tokens (see `TESTING/TEST-RESULTS.md` → "Pro vs Elite matrix audit").

| Feature (`FEATURES` key) | Min tier | Enforced by | Surfaced on |
|---|---|---|---|
| Unlimited analyses (`unlimited_analyses`) | Pro | `enforce_analysis_limit`, `enforce_photo_limit` (free = `FREE_ANALYSIS_LIMIT`) | /upload, /results |
| Full AI report (`full_report`) | Pro | `require_pro` → `GET /analysis/{id}/report` | /results, /glow-up |
| Daily AI coach (`ai_coach`) | Pro | `require_pro` → `GET /coach` | /coach (entire page) |
| Glow-Up Forecast (`glow_up_forecast`) | Pro | `require_pro` → `GET /analysis/{id}/insights` | /glow-up, /results |
| Percentile Rank (`percentile_rank`) | Pro | same endpoint as forecast | /glow-up, /results |
| Look-Alike Archetype (`archetype_match`) | Pro | same endpoint as forecast | /glow-up, /results |
| Arc quest claiming (`arc_engine`) | Pro | `require_pro` → `POST /arc/quests/{id}/claim` | /arc |
| Golden-Ratio Harmony Map (`golden_ratio`) | Elite | `require_elite` → `GET /analysis/{id}/harmony` | /glow-up, /results |
| Weekly Glow-Up Blueprint (`weekly_blueprint`) | Elite | same endpoint as harmony | /glow-up |
| Shareable Glow-Up Card (`glow_up_card`) | Elite | same endpoint as harmony | /results, /glow-up |
| Day-90 full reveal (`glow_full_reveal`) | Elite | `require_elite` → `GET /glow/full-reveal` | /glow |
| Your transformation movie (`glowups_movie`) | Elite | `require_elite` → `GET /glowups/movie`, `POST /glowups/movie/generate` | /glowups |
| Daily Glow reveal (`glow_daily`) | Free | — | /glow |
| Anonymized transformations (`glowups_feed`) | Free | — | /explore → /glowups |

### 2.1 Advertised as Pro/Elite but *not* enforced (DEF-012)

These are reachable by free members today. The UI no longer promises a tier for
them; decide per feature whether to gate (add `require_pro`) or to keep them as
free hooks and drop them from the Pro bullets:

| Feature | Current state | Endpoint |
|---|---|---|
| 90-day plan + check-ins | free | `GET /plan`, `POST /plan/checkin` |
| Progress tracking / before-after | free | `GET /progress/*` |
| Product recommendations | free (public) | `GET /products/*`, `GET /analysis/{id}/recommendations` |
| Arc XP / level / badges | free (only claiming is Pro) | `GET /arc/state`, `GET /arc/badges` |

**No phantom features.** `FEATURES` must describe shipped behaviour only. The old
"1:1 coach Q&A" Elite perk (still in the pre-2026-09-16 docs and in a stale local
build) has no endpoint and no UI, and was removed from the marketing copy.

### 2.2 Where the tier is shown (menus)

One rule: **a destination that needs a paid tier says so before the tap, and every
lock comes with the way to buy it.**

| Menu | Behaviour |
|---|---|
| Primary nav — desktop (`TopNav`) and mobile (`BottomNav`) | `Coach` carries a padlock; its accessible name is "Coach Pro". Free tabs carry nothing. |
| Glow sub-nav (`GlowSubNav`) | `Insights` and `Simulator` carry a "Pro" chip; `Daily` and `Journey` do not (both give free members something real: the daily reveal, and XP/level/badges). |
| Avatar drawer (mobile) | `Upgrade` (free) / `Subscription` (paid) → /upgrade or /settings. |
| Dashboard "Unlock the full picture" | Two labelled groups — **Pro unlocks** and **Elite only** — each row backed by the `/entitlements` `tier` field, CTA "See Pro & Elite". |
| /arc | "Upgrade to Pro" sits next to the quest lock (was a dead end). |
| /glowups | "Upgrade to Elite" in the movie card; /explore's Glow-Ups card carries an Elite chip and says the feed itself is free. |
| /glow-up, /peak-you, /results, /coach, /upload | `PaywallLock` card naming the exact plan ("Upgrade to Pro" / "Upgrade to Elite"). |

Implementation: minimum tier per destination lives in `frontend/src/lib/nav.ts`
(`GATED_DESTINATIONS` + `navTier()`), chips are `components/ui/LockChip.tsx`, and
plan names come from `frontend/src/lib/tiers.ts` (`tierLabel()`) so no screen can
hand-write a plan name again.

### 2.3 Naming rules

- **"Pro" / "Elite" = plans only.** Score bands must not borrow the words: the
  ≥80 band is now "Exceptional symmetry" (was "Elite symmetry", which read like a
  plan on a free report — DEF-013).
- Alpha order in copy: "Pro & Elite", never "Elite and Pro" — the cheaper plan is
  the ask; Elite is the anchor.

### 2.4 Pricing display (psychology, see `PSYCHOLOGY.md` §5)

- Tier cards render **Elite → Pro → Free** with badges: Elite "Best value", Pro "Most popular", Free "Start here".
- Prices lead with **monthly** (`$9.99` / `$19.99`), then show annual as a strike-through savings comparison: `~~$119.88~~ → $50.40/yr`, `~~$239.88~~ → $100.80/yr`.
- **$1 first month** (Pro monthly, one-time — `User.has_used_first_month_offer`) and a **7-day free trial** (Elite, card required) are surfaced in `/upgrade`.

## 3. Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/entitlements` | ✅ | tier, limits (used/allowed/remaining), feature matrix with `locked` flags |
| GET | `/coach` | Pro | daily AI tip (DeepSeek cached by user+date, template fallback) |
| GET | `/analysis/{photo_id}/report` | Pro | full written report (breakdown, weakest/strongest, recommendations) |
| GET | `/analysis/{photo_id}/insights` | Pro | forecast + percentile rank + archetype |
| POST | `/arc/quests/{quest_id}/claim` | Pro | claim quest XP |
| GET | `/analysis/{photo_id}/harmony` | Elite | golden-ratio harmony map + weekly blueprint + share card |
| GET | `/glow/full-reveal` | Elite | Day-90 zero-blur reveal |
| GET | `/glowups/movie`, POST `/glowups/movie/generate` | Elite | transformation movie |
| POST | `/payments/checkout` | ✅ | Stripe Checkout session → `{checkout_url}` |
| POST | `/payments/webhook` | ❌ (signed) | Stripe webhook → grants subscription + audit row |

Removed: `POST /payments/test-upgrade` no longer exists (404); dev tier changes go
through the admin API (`PATCH /admin/users/{id}/tier`).

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
- There is no client-triggerable tier flip: `test-upgrade` was removed and tier
  changes are admin-only (`PATCH /admin/users/{id}/tier`).

## 6. Frontend "trap" UX (curiosity at every point)

- `PaywallLock` component — blurred teaser + 🔒 + the exact plan name ("Upgrade to Pro" / "Upgrade to Elite").
- Dashboard `ProPerks` — two labelled groups ("Pro unlocks" / "Elite only"), each
  row carrying its own chip so a mixed list is never ambiguous.
- Results — free users see a locked "Full report" card after the free breakdown.
- Upload — free users who hit the 1-analysis limit see the paywall *before* uploading.
- `/coach` — Pro page; free users see the locked state with the teaser.
- Nav hints (`lib/nav.ts` + `LockChip`) — Coach on both navs, Insights/Simulator on
  the Glow sub-nav, Elite chip on Explore's Glow-Ups card.
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
- `STRIPE_FIRST_MONTH_COUPON_ID` (Stripe coupon, `duration=once`, `amount_off=899` USD) — powers the $1 first month
- `STRIPE_ELITE_TRIAL_DAYS=7` — Elite free trial length
- `ALLOW_TEST_PAYMENTS=1`, `ENVIRONMENT=production`
- `FREE_ANALYSIS_LIMIT=1`, `FRONTEND_URL=http://localhost:3000`
