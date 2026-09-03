# LookMaxx — Frontend

Next.js 15 (App Router) client for the LookMaxx API. This is the **client island** layer: the marketing landing page is server-rendered for SEO, and the authenticated app is a set of client screens that talk to the FastAPI backend.

## Stack

- **Next.js 15 (App Router)** + **React 19** + **TypeScript (strict)**
- **Tailwind CSS v4** (design tokens map 1:1 to `PRODUCT_SPEC.md` §6)
- **TanStack Query v5** (server state, caching, retries)
- **react-hook-form + Zod** (forms mirror backend Pydantic models)
- **Framer Motion** (score reveal, transitions — respects `prefers-reduced-motion`)
- **sonner** (toasts) · **lucide-react** (icons) · **browser-image-compression** (upload)

## Getting started

```bash
cd frontend
npm install
cp .env.example .env.local   # optional; falls back to the production API
npm run dev                   # http://localhost:3000
```

Type-check and build:

```bash
npm run typecheck
npm run build
```

The app talks to `NEXT_PUBLIC_API_URL` (default `https://lookmaxx-api.onrender.com/api/v1`).

## Route map (§7.1)

| Route | Auth | Purpose |
|---|---|---|
| `/` | ❌ | Landing |
| `/signup`, `/login` | ❌ | Auth |
| `/privacy`, `/terms` | ❌ | Legal stubs (full text in `docs/`) |
| `/onboarding` | ✅ | 3 skippable micro-steps |
| `/dashboard` | ✅ | Home: score, streak, next action |
| `/upload` | ✅ | Capture/pick → direct Cloudinary |
| `/analyzing/[photo_id]` | ✅ | Poll analysis |
| `/results/[photo_id]` | ✅ | Score reveal |
| `/plan`, `/progress`, `/explore`, `/products` | ✅ | Core app |
| `/upgrade`, `/settings` | ✅ | Paywall, account |

## Never-crash infrastructure (§7.3)

- **`src/lib/api/client.ts`** — single `apiFetch()`: attaches bearer token, parses JSON defensively, normalizes FastAPI `{detail}` (string *or* array), maps network/timeout, fires the global 401 handler, never logs secrets.
- **`src/lib/zod.ts`** — every response schema uses `.catch()` fallbacks so a malformed field degrades to a safe default, never a throw.
- **`src/hooks/useRequireAuth.ts`** — redirects on missing token or 401 only (network errors render the screen's own retry state).
- **`error.tsx` / `global-error.tsx` / `not-found.tsx`** — branded recovery, never a blank screen.

## Privacy notes (ship-gates)

- **Explore** renders score deltas only — raw face URLs from `/explore` are **never rendered** until the blur/opt-in fix ships (§5.11, §20.5).
- **Paywall** shows a "join waitlist" state — no fake checkout until `/payments/*` exists (§12.4).
- Gating is **server-authoritative**: entitlements come from `GET /auth/me` (DB read per request), never from localStorage or the JWT.
