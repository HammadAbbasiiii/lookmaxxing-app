# LookMaxx — Admin Site & User-Tracking System
**Engineering Design Document (v1)** — *written before implementation*

## 1. Purpose

Build a complete, owner-manageable admin + analytics system so you can:

- **Add / edit / remove / deactivate products any time** (no more editing JSON or code, no redeploys).
- See a full **360° view of every user** (20+ data points): photos uploaded, pics actually watched, time spent, where they quit, and how far they got toward paying.
- Understand the **whole funnel** (landing → signup → upload → score → plan → upgrade) and find exactly where people drop off.

Everything is **self-hosted, privacy-first (no PII in the event log), every error handled, secured, and locked behind an admin gate.**

---

## 2. Your direct questions — answered

**Q1: Do I need an admin site to add/remove products anytime?**
Yes. Today products live in a static JSON file (`backend/app/services/product_database.json`), so every add/remove is a code change + redeploy. The admin site gives you a **Products page** (table + form) to create, edit, archive (soft-delete) and re-activate products instantly, with images and affiliate links. **No redeploys.**

**Q2: Can I track image count, photo viewing, time spent, page-quit, and payment/pro intent?**
Yes. We extend the existing `/api/v1/track` event system with a full taxonomy (Section 3), then aggregate it into per-user and site-wide dashboards.

**Q3: "At least 20 points per user" — what should we track?**
We track ~30 raw *events* and derive a 20+ field **User 360 profile** from them (Section 3.3). The events are chosen from established product-growth research (Section 3.1), not guesses.

---

## 3. Research: what to track & why

### 3.1 Frameworks the taxonomy is built on
- **AARRR (Pirate Metrics)** — Acquisition, Activation, Retention, Revenue, Referral (Dave McClure). Every event maps to one of these.
- **Activation / "aha moment"** — for LookMaxx the aha moment is **seeing your first analysis score**. Time-to-value (TTFV) = signup → first score. Users who reach it in session #1 retain dramatically better → track `first_score_viewed` and TTFV.
- **North Star Metric** — **"Weekly active users who complete a check-in"** (habit = retention; the Duolingo-streak effect). All engagement tracks toward this.
- **Funnel analysis** — the visit → signup → upload → score → plan → upgrade steps, measuring drop-off at each stage.
- **Peak-End Rule (Kahneman)** — users judge an experience by its **peak** (first score reveal) and its **end** (celebration). This tells us *where* to put confetti/milestone rewards, and we track whether those moments are being reached.

### 3.2 The event taxonomy (~30 events)

**(A) Acquisition — anonymous, no PII**
1. `landing_view` — landing page, referrer, UTM source/campaign/medium.
2. `page_view` — any page (already tracked).

**(B) Activation funnel**
3. `signup_start`
4. `signup_complete`
5. `onboarding_step` — which step (1..N) → find where onboarding drops.
6. `onboarding_complete`
7. `photo_upload_start`
8. `photo_upload_complete`
9. `analysis_start`
10. `analysis_complete`
11. `first_score_viewed` ← the **aha moment**.

**(C) Core engagement — what they actually do**
12. `gallery_opened` — watching their pics.
13. `photo_viewed` — which photo (count = "pics actually watched").
14. `before_after_view` — comparing progress (strong intent signal).
15. `checkin_complete`
16. `streak_milestone` — day 7/14/21/30 (Peak-End reward points).
17. `plan_viewed`
18. `task_completed` — daily plan task.
19. `article_viewed` / `article_read` — explore/education.
20. `product_viewed` / `product_click` — affiliate intent.

**(D) Monetization / payment intent — "did they go to pay, or quit before?"**
21. `pricing_viewed`
22. `upgrade_click` (already tracked)
23. `checkout_started`
24. `checkout_completed`
25. `payment_failed`
26. `plan_cancelled`
27. `upgrade_abandoned` — visited upgrade/checkout but left without paying.

**(E) Retention / churn signals**
28. `page_exit` — page + duration_ms (already tracked) → "where they quit".
29. `session_start` / `session_end` — session length + device.
30. `feedback_submitted` — ratings/comments.

Each event stores only `event_name + page + referrer + properties{} + user_id(optional) + session_id + created_at`. **No faces, no emails, no tokens.**

### 3.3 The User 360 profile (20+ derived points, per user)
1. Email + name *(admin only)*
2. Account created date / days since signup
3. Subscription tier + is_subscribed
4. Onboarding completed (y/n)
5. Photos uploaded (count)
6. Photos analyzed (count)
7. Baseline score (first photo)
8. Latest score
9. Score delta (improvement)
10. Total check-ins
11. Current streak
12. Longest streak
13. Plan day (current/total) + active?
14. Total time in app (sum of durations)
15. Session count
16. Last seen (last event time)
17. Pages viewed (count + top 5)
18. Photos viewed (count) ← "pics actually watched"
19. Products viewed / clicked
20. Pricing/upgrade page views
21. Checkout started / completed (current funnel stage)
22. Last page before quit ← "where they quit"
23. Funnel stage label (e.g. Active / At-paywall / Churned)

---

## 4. Data model changes

### 4.1 Product → move from JSON to DB
New `Product` table so the admin can CRUD it live:
`id, name, brand, category, price, tier (budget/mid_range/premium), image_url, affiliate_url, description, rating, review_count, is_active (bool), created_at, updated_at`.

A one-time migration imports `product_database.json` into the table. The recommendation & browse endpoints then read the **DB** (with results cached).

### 4.2 AdminAction audit log (manageability)
`id, admin_email, action, entity_type, entity_id, detail_json, created_at` — every admin create/edit/delete is recorded so you can see who changed what, when.

### 4.3 AnalyticsEvent (already exists)
Keep as the single event log; just expand the event vocabulary (Section 3.2). No schema change needed — it already has `properties` JSON.

---

## 5. Backend API

**Product admin (admin-only, gated by `require_admin`)**
- `GET    /api/v1/admin/products` — list + search + filter + pagination
- `POST   /api/v1/admin/products` — create
- `PUT    /api/v1/admin/products/{id}` — update
- `DELETE /api/v1/admin/products/{id}` — soft-delete (is_active=false)
- `POST   /api/v1/admin/products/{id}/activate` — re-enable
- `POST   /api/v1/admin/products/import` — bulk import from JSON (one-time)

**Analytics admin (admin-only)**
- `GET /admin/overview` — *exists*; extend with funnel + revenue KPIs
- `GET /admin/users` — *exists*; searchable list
- `GET /admin/users/{id}` — *exists*; extend to the full User 360 (Section 3.3)
- `GET /admin/funnel` — stage counts + conversion %
- `GET /admin/retention` — cohort / N-day retention
- `GET /admin/events/summary` — *exists*
- `GET /admin/events` — event explorer (filter by event/user/page/date)

All admin endpoints return a consistent `{success, data|error}` envelope with proper HTTP codes.

---

## 6. Frontend admin dashboard

A new `/admin` section (reusing the black+gold design system), protected by `is_admin`:
- **Dashboard** — KPI cards (users, DAU/WAU/MAU, activations, upgrades, revenue) + charts.
- **Users** — searchable table → click → User 360 deep-dive.
- **Products** — table + create/edit form (the "add/remove anytime" tool).
- **Analytics** — funnel, retention, event explorer.
- **Activity** — admin audit log.

---

## 7. Security & error-handling standards

- Admin gate (`require_admin`) on **every** admin route, with proper 401/403 handling.
- Pydantic validation on every input; ORM only (no SQL injection); rate-limit admin endpoints.
- Every DB write wrapped in try/except with `db.rollback()` + structured error response.
- **No PII in events** — emails appear only in admin views.
- Audit log for all mutating admin actions.
- Secrets via env (`SECRET_KEY`, `ADMIN_EMAILS`, `DATABASE_URL`).

---

## 8. Implementation phases

- **Phase 1 — Products admin:** Product model + JSON migration + CRUD API + Products admin UI. *(You can add/remove products immediately.)*
- **Phase 2 — Full tracking + analytics:** expand tracker events + `/admin/funnel` + `/admin/retention` + User 360 deep-dive + Analytics UI.
- **Phase 3 — Dashboard + audit log + polish:** KPIs, charts, audit-log UI, security hardening, caching.

---

## 9. Open questions for you

1. **Priority:** build Phase 1 (products) first, or the full tracking dashboard first?
2. **Placement:** a separate admin URL, or a `/admin` page inside the same app (simpler, recommended for MVP)?
3. **Products:** include an affiliate link + commission field per product (recommended — yes)?


---

## 10. Implemented so far (addendum)

### Admin user management (owner controls)
- `PATCH /api/v1/admin/users/{user_id}/admin` — promote/demote a user's admin flag (body `{is_admin: bool}`). Admins cannot change themselves (400); unknown user 404; idempotent when the flag already matches.
- `PATCH /api/v1/admin/users/{user_id}/tier` — override subscription tier (body `{tier: "free"|"pro"|"elite"}`). Normalizes `strip().lower()`; sets `is_subscribed = tier != "free"`; invalid tier 400.
- Every change writes an `AdminAction` audit row (`promote_admin` / `demote_admin` / `set_tier`).
- Admin user list (`GET /admin/users`) now returns `is_admin` per row.

### Admin dashboard access
- Owner email `hammadabbasi732@gmail.com` is in `ADMIN_EMAILS`, so the admin UI is reachable by logging in as that email (no `is_admin` flag required).
- `/admin` UI gate checks `me.is_admin || me.email in ADMIN_EMAILS` via an `isAdminUser()` helper.

### Frontend controls
- Admin Users table: per-row **Admin** buttons (Make admin / Revoke) and a **Tier** dropdown (free/pro/elite). The signed-in user's own row is readonly ("Admin (you)" / "you") with no self-toggle.
- User detail page (`/admin/users/[id]`): a **Manage user** card with the same admin toggle + tier select, which updates the detail facts and invalidates `admin-users`, `admin-user`, and `me` queries (so TopNav/admin gating stays in sync).
- API helpers in `frontend/src/lib/api/admin.ts`: `setUserAdmin()`, `setUserTier()`.

### Tests
- `backend/tests/test_admin.py` covers 403 gating, promote/demote + audit rows, idempotency, self-change 400, unknown-user 404, tier free/pro/elite + `is_subscribed`, invalid tier 400, and case-insensitive normalization. (Verified over HTTP in-session; full pytest run requires the complete backend env with ML deps.)

