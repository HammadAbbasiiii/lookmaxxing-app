# Architecture — LookMaxx

> Phase 1 deliverable. Evidence-based (from source), not from README alone.
> Commit at time of writing: `c9229f5` (main).

## 1. Application architecture (high level)

```
Browser (Next.js 15 App Router) --HTTP/JSON--> FastAPI (Render)
   | TanStack Query · Zod · Tailwind v4           | JWT (HS256) · SQLAlchemy
   | image bytes -> direct Cloudinary upload       | ML face analysis (lazy)
   v                                              v
Cloudinary (signed)                          Postgres · DeepSeek · Redis
```

- Client is treated as **untrusted**. Entitlements are read from the DB on every
  request via `require_*` dependencies; the JWT carries only the user id.
- Auth is **bearer-token** (no cookies) -> CORS uses an explicit origin allow-list
  with `allow_credentials=False`.

## 2. Frontend architecture

| Concern | Technology |
|---|---|
| Framework | Next.js 15 (App Router), React 19, TypeScript strict |
| Styling | Tailwind CSS v4 |
| Server state | TanStack Query v5 |
| Forms | react-hook-form + Zod (mirrors Pydantic models) |
| Animation | Framer Motion (reduced-motion aware) |
| Toasts / icons | sonner / lucide-react |
| Upload | browser-image-compression |

Key modules:
- `src/lib/api/client.ts` — `apiFetch()`: bearer token, defensive JSON parse,
  normalizes FastAPI `{detail}`, status->copy map, global 401 handler, no secret logging.
- `src/lib/api/endpoints.ts` — typed endpoints; every response Zod-decoded with `.catch()` fallbacks.
- `src/lib/zod.ts` — defensive schemas + `decode()`.
- `src/lib/auth.ts` — token get/set/clear + `UNAUTHORIZED_EVENT` bus.
- `src/hooks/useRequireAuth.ts` — route guard (missing token or 401 only).

Route groups: `(auth)` public; `(app)` authed; `admin/` admin-gated UI;
`onboarding`, `privacy`, `terms`, landing `/` public.

## 3. Backend architecture

| Concern | Technology |
|---|---|
| Framework | FastAPI 0.115.6 (Uvicorn) |
| ORM | SQLAlchemy 2.0.36 (`create_all` at boot + lightweight migrations) |
| DB | Postgres (prod), SQLite fallback |
| Auth | python-jose HS256 JWT (30-min TTL) + passlib/bcrypt |
| Rate limit | Redis sliding window (in-memory fallback) |
| Images | Cloudinary (signed) |
| AI | DeepSeek (OpenAI SDK) + deterministic fallback |
| ML | MediaPipe + PyTorch (lazy; mock fallback) |
| Payments | Stripe Checkout + signed webhook (503 until keys set) |
| Email | console (dev) / SMTP (prod) |

Middleware order (`app/main.py`): CORS -> GZip -> error handler -> rate limiter ->
**security headers (outermost)** -> routers (all under `/api/v1`).

## 4. Database architecture

Models: `User`, `Photo`, `Plan`, `UserCheckin`, `PasswordResetToken`,
`GlowState`, `GlowReveal`, `ArcState`, `UserBadge`, `Transformation` + analytics.
Notable `User` columns: `token_version`, `is_admin`, `subscription_tier`, streak fields.

## 5. Authentication architecture

Signup: normalize email (strip/lower), **password not stripped**, strength check,
bcrypt hash. Login: OAuth2 form -> JWT (`sub`+`ver`). `/auth/me` verifies
`token_version`. Reset: single-use hashed token, 30-min expiry, anti-enumeration,
per-email throttle, `token_version` bump revokes sessions. Login throttle: 10
failures / 15 min per email+IP (in-memory).

## 6. Authorization architecture

Roles: Anonymous / Authenticated / Pro (tier in {pro,elite}) / Elite (tier==elite) / Admin.
Enforced per-endpoint via `require_pro`, `require_elite`, `require_admin`.
403 carries `code:"upgrade_required"`. IDOR: photo/report access owner-scoped (404).

## 7. API architecture

REST/JSON under `/api/v1`. Errors use `{detail}` (string | 422 array | object).
Full inventory in `APPLICATION-INVENTORY.md`.

## 8. External dependencies

Cloudinary, DeepSeek, Stripe, Redis, Postgres, MediaPipe/PyTorch, SMTP.

## 9. Existing tests

Backend: 261 passing pytest tests (auth, reset, admin, products, plan, photos,
validation, insights, premium, scoring, db, security, profile/progress, glow/arc/glowups).
Frontend: `npm run typecheck` only (this pass adds Playwright).

## 10. Existing weaknesses

1. Frontend had no runtime tests (addressed this pass).
2. Rate limiter / login throttle in-memory (per-worker).
3. ML score may be heuristic/mock when MediaPipe/PyTorch unavailable.
4. `/upload/save` trusts Cloudinary URL (cloud-name substring check).
5. `datetime.utcnow()` deprecations (653 warnings) — non-blocking.
6. Stripe paths honest-fail (503) until keys configured.

## 11. Important risks

- Hand-rolled per-endpoint authz — a missed `require_*` is privilege escalation.
- In-memory rate limiting does not scale horizontally.
- Client-server contract drift (Zod vs Pydantic).

## 12. Proposed testing strategy

Unit + API + E2E + a11y + responsive + cross-browser + security (dependency
audit + header checks + static review) + visual regression. Full matrix in
`TEST-MATRIX.md`.

