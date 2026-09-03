# MEMORY.md — the "brain" (read THIS first, not the whole repo)

One compact state snapshot. The coding agent reads only this file at session start to avoid re-discovering the project. **Update it at the end of every task.**

## Project
LookMaxx — web-only MVP. Backend (FastAPI) is **live** at `https://lookmaxx-api.onrender.com/api/v1`. Frontend is **not built yet**.

## Docs (the sources of truth)
- `PRODUCT_SPEC.md` — ⭐ **master whole-product design spec** (every screen/button/error, security, psychology, monetization/gating, **privacy/GDPR §20**, **production ops §21**, performance, run/deploy). Tie-breaker over the others.
- `PSYCHOLOGY.md` — conversion/design/psychology tokens. ✅ complete.
- `ROADMAP.md` — MVP checklist: 14 screens, API map, 20 signup scenarios, error catalog. ✅ complete.
- `CONTEXT.md` — backend ground truth, credentials, gaps. ✅ complete.

## Tech decisions (LOCKED)
- Frontend: Next.js 15 App Router + TypeScript strict + Tailwind v4 + TanStack Query v5 + react-hook-form + Zod + Framer Motion + sonner + lucide-react → deploy Vercel.
- Auth token: `localStorage` (V1) → httpOnly cookie (Phase 2).
- Upload: **direct Cloudinary** (`/upload/signature` → Cloudinary → `/upload/save`), NOT multipart to backend.

## Credentials status
- Cloudinary: ✅ in `backend/.env` (`dguvrhmt` / …).
- DeepSeek: ✅ both keys verified working (`apiforwebapp` local + `apiforrender` on Render). Model default `deepseek-chat` (non-reasoning, cheaper); configurable via `DEEPSEEK_MODEL`.
- SECRET_KEY: ✅ generated local value.
- DATABASE_URL: local SQLite ✅; **Render Postgres ❌ missing**.
- REDIS_URL: local ✅; Render Redis ❌ (optional — in-memory limiter is fine for V1).
- Stripe: ❌ none + **no backend route yet**.

## Backend gaps (honest)
ML falls back to mock/heuristic if unavailable; in-memory rate limiter; CORS `*`; `/upload/save` trusts the Cloudinary URL. Stripe route now exists (`/payments/*`) but needs real keys + price IDs.

## Analytics & admin (added)
- **Self-hosted analytics:** `POST /api/v1/track` (batched events, auth optional) + `AnalyticsEvent` model. Frontend: `lib/api/analytics.ts` `track()` + `components/AnalyticsTracker.tsx` (page_view / page_exit time-spent / session). Events carry no PII.
- **Admin endpoints (gated by `require_admin`):** `/admin/overview`, `/admin/users`, `/admin/users/{id}`, `/admin/events/summary`. Access = `is_admin` flag **or** email in `ADMIN_EMAILS` env (comma-separated). Set `ADMIN_EMAILS` on Render to unlock.
- **Admin user management:** `PATCH /api/v1/admin/users/{id}/admin` (promote/demote) + `PATCH /api/v1/admin/users/{id}/tier` (override free/pro/elite, sets `is_subscribed`). Both write `AdminAction` audit rows (`promote_admin`/`demote_admin`/`set_tier`); self-admin change is 400; idempotent. Admin list now returns `is_admin`. Frontend: Users table Admin buttons + Tier dropdown, and a "Manage user" card on `/admin/users/[id]` (`setUserAdmin`/`setUserTier` in `lib/api/admin.ts`), with `sonner` toasts + invalidation of `admin-users`/`admin-user`/`me`. Owner access via `ADMIN_EMAILS` (hammadabbasi732@gmail.com).
- **Migration:** `main.py` auto-adds `users.is_admin` if missing; `analytics_events` table auto-created by `create_all`.
- **Products page** now browses the full `product_database.json` via `/products/category/{cat}` + search + images (was: single personalized rec only).

## Premium, entitlements & payments (added)
- **Server-authoritative gating:** `require_pro` / `require_elite` in `dependencies.py`; 403 carries `{code:"upgrade_required"}`. `GET /entitlements` returns tier + limits + a feature matrix (locked/unlocked + teasers) from `services/entitlements_service.py`.
- **Freemium limit:** free = 1 analysis (`FREE_ANALYSIS_LIMIT`, default 1). Enforced in `/upload/save`, `/photos/upload`, `/photos/analyze/{id}`.
- **Premium features:** `GET /coach` (daily AI tip, DeepSeek + fallback, cached by user+date), `GET /analysis/{id}/report` (full written report).
- **Creative premium insights (added):** `GET /analysis/{id}/insights` (Pro — Glow-Up Forecast, Percentile Rank, Look-Alike Archetype) and `GET /analysis/{id}/harmony` (Elite — Golden-Ratio Harmony Map, Weekly Blueprint, Shareable Glow-Up Card). All deterministic + gender-aware in `services/insights_service.py` (pure, no ML/network). Surfaced in the results page + upgrade page + entitlements matrix.
- **Bidirectional admin/user switch (added):** admins share one account for both roles — TopNav "Admin" badge goes user→admin, the admin layout now has "View app as user" going admin→user, and `AdminModeBanner` shows an "Admin · browsing as user" sign on every user screen with a one-tap return to `/admin`.
- **Payments (honest):** `POST /payments/checkout` → Stripe Checkout; `POST /payments/webhook` → grant subscription + audit row; `POST /payments/test-upgrade` (dev-only, `ALLOW_TEST_PAYMENTS=1` + non-production). No fake charges — missing keys → 503 waitlist.
- **Profile data:** `User` gains `skin_type`, `skin_concerns`, `commitment` (auto-migrated in `main.py`); onboarding is now 5 steps; settings editable. All inputs server-validated.
- **Frontend:** `PaywallLock`, `useEntitlements`, `/coach` page, dashboard `ProPerks`, results/upload paywall teasers, upgrade wired to real checkout (waitlist fallback).

## ✅ Face-detection blocker — FIXED & deployed
- Previously: live upload → analysis always failed at face detection (`"No face detected"`).
- Fixed and **deployed on Render (commit `56915f9`)**: 5× same-image scores are deterministic; category scores clamped 30–95; corrupt image returns a clean 400. Backend confirmed 100.

## Next steps (ordered)
1. Deploy frontend to Vercel (landing + app).
2. Verify Render boot logs (`✅ DB tables ready`, `🌱 Seeded N products`).
3. Add Stripe keys + price IDs on Render to enable real checkout (route already built).
4. Smoke-test premium: `/upgrade` checkout (or `ALLOW_TEST_PAYMENTS=1` preview), `/coach`, `/admin`.
5. Legal/compliance: privacy policy, consent log, DPIA, sub-processor DPAs (`PRODUCT_SPEC.md` §20).
6. Move rate limiter to Redis + lock CORS to the Vercel domain before real traffic.

## Still needed from the user
1. Render Postgres `DATABASE_URL`.
2. (optional) Render Redis URL.
3. Stripe secret key + webhook secret + price IDs (`STRIPE_PRICE_PRO_*`, `STRIPE_PRICE_ELITE_*`) — required to enable real checkout (route already built).
4. Confirm the Render prod DeepSeek key = `apiforrender` (sk-b5c32…73bd).
5. Legal review of the `docs/` drafts (privacy policy, terms, DPIA) by a qualified lawyer before public launch.
6. Set `ADMIN_EMAILS` env on Render (comma-separated) to unlock `/admin/*`.
