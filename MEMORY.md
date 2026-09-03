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
No Stripe/payments route; ML falls back to mock/heuristic if unavailable; in-memory rate limiter; CORS `*`; `/upload/save` trusts the Cloudinary URL.

## ✅ Face-detection blocker — FIXED & deployed
- Previously: live upload → analysis always failed at face detection (`"No face detected"`).
- Fixed and **deployed on Render (commit `56915f9`)**: 5× same-image scores are deterministic; category scores clamped 30–95; corrupt image returns a clean 400. Backend confirmed 100.

## Next steps (ordered)
1. Scaffold Next.js in `frontend/` per `PRODUCT_SPEC.md` §8.
2. Auth (signup/login/me + the 20 scenarios in `PRODUCT_SPEC.md` §9.2).
3. Upload → analyze → result (direct Cloudinary flow).
4. Dashboard / plan / streak.
5. Stripe backend (`require_pro` + `/payments/*`) + `/upgrade`.
6. Legal/compliance: privacy policy, consent log, DPIA, sub-processor DPAs (`PRODUCT_SPEC.md` §20).

## Still needed from the user
1. Render Postgres `DATABASE_URL`.
2. (optional) Render Redis URL.
3. Stripe secret key + webhook secret (only when building payments).
4. Confirm the Render prod DeepSeek key = `apiforrender` (sk-b5c32…73bd).
5. Legal review of the `docs/` drafts (privacy policy, terms, DPIA) by a qualified lawyer before public launch.
