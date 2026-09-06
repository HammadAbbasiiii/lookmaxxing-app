# Application Inventory — LookMaxx

> Phase 2 deliverable. Every frontend route and backend endpoint, mapped from
> source (`frontend/src/app/**`, `backend/app/routes/*`).

## 1. Frontend routes

| Route | Group | Auth | Purpose | API deps |
|---|---|---|---|---|
| `/` | — | ❌ | Landing | — |
| `/signup` | (auth) | ❌ | Registration | POST /auth/signup |
| `/login` | (auth) | ❌ | Login | POST /auth/login |
| `/forgot-password` | (auth) | ❌ | Request reset | POST /auth/forgot-password |
| `/reset-password` | (auth) | ❌ | Set new password | GET /auth/reset-password/verify, POST /auth/reset-password |
| `/onboarding` | — | ✅ | 3 skippable micro-steps | POST /profile/onboarding |
| `/privacy`, `/terms` | — | ❌ | Legal stubs | — |
| `/dashboard` | (app) | ✅ | Score, streak, next action | GET /dashboard, /auth/me |
| `/upload` | (app) | ✅ | Capture/pick → Cloudinary | GET /upload/signature, POST /upload/save |
| `/analyzing/[photo_id]` | (app) | ✅ | Poll analysis | GET /photos/{id}/status |
| `/results/[photo_id]` | (app) | ✅ | Score reveal | GET /analysis/{id}, /report, /insights, /harmony |
| `/plan` | (app) | ✅ | 90-day plan | GET /plan, POST /plan/checkin |
| `/progress` | (app) | ✅ | Before/after | GET /progress/*, /photos/* |
| `/explore` | (app) | ✅ | Anonymized feed | GET /explore |
| `/products` | (app) | ✅ | Affiliate recs | GET /products/recommendations, /categories, /category/{c} |
| `/upgrade` | (app) | ✅ | Paywall | GET /entitlements, POST /payments/checkout |
| `/settings` | (app) | ✅ | Account/profile | GET /profile, PUT /profile, DELETE /profile/delete |
| `/coach` | (app) | ✅ (Pro) | Daily AI coach | GET /coach |
| `/glow` | (app) | ✅ | Daily reward | GET /glow/state, POST /glow/open, GET /glow/reveals |
| `/arc` | (app) | ✅ | RPG XP/levels/quests | GET /arc/state, /badges, POST /arc/quests/{id}/claim |
| `/glowups` | (app) | ✅ | Transformation feed | GET /glowups/feed, /consent, POST /consent |
| `/peak-you` | (app) | ✅ | Future-self projection | (insights-based) |
| `/admin` + subpages | admin | 🔐 | Analytics/user mgmt | GET /admin/* |

## 2. Backend API endpoints

Base: `/api/v1`. Auth: ❌ none · ✅ bearer · 🅿️ Pro · 👑 Elite · 🔐 admin.

### Health / Auth
| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | /health | ❌ | Liveness + Redis/memory |
| GET | / | ❌ | Root |
| POST | /auth/signup | ❌ | Create account |
| POST | /auth/login | ❌ | OAuth2 form → JWT |
| GET | /auth/me | ✅ | Current user |
| POST | /auth/logout | ✅ | No-op |
| POST | /auth/forgot-password | ❌ | Reset link (anti-enumeration) |
| GET | /auth/reset-password/verify | ❌ | Token validity |
| POST | /auth/reset-password | ❌ | Set new password |

### Photos / upload / analysis
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | /photos/upload | ✅ | Multipart → bg analysis |
| GET | /photos/all | ✅ | List photos |
| DELETE | /photos/{photo_id} | ✅ | Delete photo |
| GET | /photos/{photo_id}/status | ✅ | Status/score |
| POST | /photos/analyze/{photo_id} | ✅ | Trigger analysis |
| GET | /upload/signature | ✅ | Cloudinary signed params |
| POST | /upload/save | ✅ | Register direct-upload URL |
| GET | /analysis/{photo_id} | ✅ | Scores + face shape |
| GET | /analysis/{photo_id}/report | ✅ 🅿️ | Written report |
| GET | /analysis/{photo_id}/plan | ✅ | 90-day plan |
| PUT | /analysis/{photo_id}/plan/progress | ✅ | Phase/week update |
| GET | /analysis/progress/all | ✅ | Score timeline |
| GET | /analysis/{photo_id}/recommendations | ✅ | Personalized recs |
| GET | /analysis/{photo_id}/insights | ✅ 🅿️ | Forecast/percentile/archetype |
| GET | /analysis/{photo_id}/harmony | ✅ 👑 | Golden-ratio map + blueprint |

### Plan / progress / dashboard / explore / products
| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | /plan | ✅ | Active plan + milestones |
| POST | /plan/checkin | ✅ | Log check-in (streak) |
| GET | /plan/progress | ✅ | Plan progress |
| GET | /progress/history | ✅ | Score history |
| GET | /progress/checkins | ✅ | Check-in log |
| POST | /progress/checkin | ✅ | Check-in |
| GET | /progress/milestones | ✅ | Milestones |
| GET | /progress/streak | ✅ | Streak |
| GET | /progress/photos | ✅ | Photos |
| GET | /progress/photos/baseline | ✅ | Baseline photo |
| GET | /progress/photos/latest | ✅ | Latest photo |
| GET | /progress/photos/compare | ✅ | Before/after compare |
| POST | /progress/photos/upload | ✅ | Upload progress photo |
| GET | /dashboard | ✅ | Home aggregate |
| GET | /explore | ✅ | Anonymized feed |
| GET | /products/recommendations | ✅ | Personalized recs |
| GET | /products/category/{category} | ✅ | By category |
| GET | /products/categories | ✅ | Categories |

### Profile / entitlements / momentum
| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | /profile | ✅ | Profile |
| PUT | /profile | ✅ | Update profile |
| POST | /profile/onboarding | ✅ | Onboarding save |
| DELETE | /profile/delete | ✅ | GDPR account deletion |
| GET | /entitlements | ✅ | Tier + limits + feature matrix |
| GET | /glow/state | ✅ | Glow state |
| POST | /glow/open | ✅ | Open today's reward |
| GET | /glow/reveals | ✅ | Reveal history |
| GET | /glow/full-reveal | ✅ 👑 | Full reveal |
| GET | /arc/state | ✅ | XP/level/quests |
| POST | /arc/quests/{quest_id}/claim | ✅ 🅿️ | Claim quest XP |
| GET | /arc/badges | ✅ | Badges |
| GET | /glowups/feed | ✅ | Transformation feed |
| POST | /glowups/consent | ✅ | Set share consent |
| GET | /glowups/consent | ✅ | Get consent |
| GET | /glowups/movie | ✅ 👑 | Transformation movie |
| POST | /glowups/movie/generate | ✅ 👑 | Generate movie |
| POST | /glowups/items/{item_id}/report | ✅ | Report item |
| GET | /coach | ✅ 🅿️ | Daily AI coach tip |

### Payments / admin
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | /payments/checkout | ✅ | Stripe session (503 if unconfigured) |
| POST | /payments/webhook | ❌ (signed) | Stripe webhook |
| POST | /payments/test-upgrade | ✅ | Dev-only tier flip |
| POST | /analytics/track | optional | Event tracking |
| GET | /admin/overview | 🔐 | Analytics overview |
| GET | /admin/users | 🔐 | User list |
| GET | /admin/users/{user_id} | 🔐 | User 360 |
| PATCH | /admin/users/{user_id}/admin | 🔐 | Promote/demote |
| PATCH | /admin/users/{user_id}/tier | 🔐 | Tier override |
| GET | /admin/events/summary | 🔐 | Event summary |
| GET | /admin/funnel | 🔐 | Funnel |
| GET | /admin/retention | 🔐 | Retention |
| GET | /admin/events | 🔐 | Events |
| GET | /admin/activity | 🔐 | Activity |
| GET | /admin/products | 🔐 | Product list |
| POST | /admin/products | 🔐 | Create product |
| PUT | /admin/products/{product_id} | 🔐 | Update product |
| DELETE | /admin/products/{product_id} | 🔐 | Delete product |
| POST | /admin/products/{product_id}/activate | 🔐 | Activate |
| POST | /admin/products/import | 🔐 | Import |

## 3. Key shared states / edge cases

- Score clamp 30–95; deterministic fallbacks when ML/AI unavailable.
- Freemium: free tier hard-capped at 1 analysis/photo.
- Streak: once-per-day check-in (409 on duplicate), gap resets streak.
- Glow: one reveal per user per calendar day (idempotent).
- Arc: quests regenerated per UTC date; XP idempotency via `xp_events` ledger.
- Glow-Ups: share opt-in only; movie render throttled 1/day; report/soft-delete moderation.

