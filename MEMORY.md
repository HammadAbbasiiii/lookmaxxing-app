# MEMORY.md — the "brain" (read THIS first, not the whole repo)

One compact state snapshot. The coding agent reads only this file at session start to avoid re-discovering the project. **Update it at the end of every task.**

## Project
LookMaxx — web-only MVP. Backend (FastAPI) is **live** at `https://lookmaxx-api.onrender.com/api/v1`. Frontend is **not built yet**.

## Docs (the 3 sources of truth)
- `PSYCHOLOGY.md` — conversion/design/psychology. ✅ complete.
- `ROADMAP.md` — full spec: 14 screens, API map, **20 signup scenarios**, error catalog, Stripe plan, testing, milestones. ✅ complete.
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

## 🔴 Live blocker (found via live test)
- Live upload → analysis **always fails** at face detection (`"No face detected"`) — verified on Render with a real test account + Obama/Lena/Biden photos. The ML model / heuristic **never runs**, so the model-vs-mock question is moot until this is fixed.
- Root cause: `validation_service._detect_face` returns `False` immediately when MediaPipe loads but finds no face (never falls back to Haar), combined with MediaPipe failing at runtime (truncated `face_landmarker.task` or numpy 2.x).
- Fixes applied (local, **not deployed**):
  1. `app/services/validation_service.py` — fall through to Haar cascade on MediaPipe miss.
  2. `app/services/face_service.py` — require model file > 1 KB (ignore empty/truncated).
  3. `render.yaml` — `set -e` + `test -s` so a failed/empty download breaks the build.
  4. `requirements.txt` — pin `numpy==1.26.4`.

## Next steps (ordered)
1. **Deploy the face-detection fixes** (commit + push to `github.com/HammadAbbasiiii/lookmaxxing-app` → Render redeploys), then re-run the model-vs-mock test (upload the same photo twice; identical scores = real model, differing = random fallback).
2. Scaffold Next.js in `frontend/`.
3. Auth (signup/login/me + the 20 scenarios in ROADMAP §9).
4. Upload → analyze → result (direct Cloudinary flow).
5. Dashboard / plan / streak.
6. Stripe backend + `/upgrade`.

## Still needed from the user
1. Render Postgres `DATABASE_URL`.
2. (optional) Render Redis URL.
3. Stripe secret key + webhook secret (only when building payments).
4. Confirm the Render prod DeepSeek key = `apiforrender` (sk-b5c32…73bd).
