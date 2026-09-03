# LookMaxx — Project Context & Current State

> Operational snapshot of what exists, what's live, what's missing, and what to do next.
> This file is **factual** — update it whenever reality changes.

---

## 1. Status at a glance

| Area | Status |
|---|---|
| Backend | ✅ **Built & live** at `https://lookmaxx-api.onrender.com/api/v1` |
| Frontend | ❌ **Empty** — only `frontend/.gitkeep` exists |
| Monetization (Stripe) | ❌ **Not built** — no billing route; only `User` model fields exist |
| Design system | 📄 Spec'd in `PSYCHOLOGY.md` (not yet coded) |
| Credentials | ✅ Cloudinary + DeepSeek (local) set · ⚠️ Render DB/Redis + Stripe missing |
| ML | ⚠️ Lazy-loaded; **falls back to mock/heuristic** if model/OOM |

---

## 2. Repository layout

```
lookmaxx-web/
├── PSYCHOLOGY.md        # conversion/design psychology (foundation)
├── ROADMAP.md           # web MVP spec + edge cases + errors
├── CONTEXT.md           # this file
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, routers, CORS, GZip, middleware
│   │   ├── config.py             # Settings from env
│   │   ├── database.py           # SQLAlchemy engine/session
│   │   ├── models.py             # User, Photo, Plan, UserCheckin
│   │   ├── schemas.py            # Pydantic request/response
│   │   ├── dependencies.py       # JWT, bcrypt, get_current_user
│   │   ├── middleware/           # error_handler, rate_limit (in-memory)
│   │   ├── routes/               # health, auth, photos, upload, analysis,
│   │   │                         # plan, products, profile, progress, dashboard, explore
│   │   ├── services/             # prediction, face_analysis, face, deepseek, ai,
│   │   │                         # plan_generator, background_analysis, upload, quality, validation
│   │   └── ml/                   # rank_info_net_full.pth (94MB, gitignored)
│   ├── tests/                    # auth, database, validation, plan, photos
│   ├── requirements.txt · Dockerfile · render.yaml
└── frontend/
    └── .gitkeep                  # to be replaced by the Next.js app
```

---

## 3. Backend API surface (live)

Base: `https://lookmaxx-api.onrender.com/api/v1`

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | ❌ | Liveness + Redis/memory |
| POST | `/auth/signup` | ❌ | Create account |
| POST | `/auth/login` | ❌ | OAuth2 form login → JWT |
| GET | `/auth/me` | ✅ | Current user |
| POST | `/auth/logout` | — | No-op (client discards token) |
| POST | `/photos/upload` | ✅ | Multipart upload → bg analysis |
| GET | `/photos/{id}` | ✅ | Photo status/score |
| POST | `/photos/analyze/{id}` | ✅ | Trigger analysis |
| GET | `/upload/signature` | ✅ | Cloudinary signed params |
| POST | `/upload/save` | ✅ | Register direct-upload URL |
| GET | `/analysis/{photo_id}` | ✅ | Scores + face shape |
| GET | `/analysis/{photo_id}/plan` | ✅ | 90-day plan |
| PUT | `/analysis/{photo_id}/plan/progress` | ✅ | Update phase/week |
| GET | `/analysis/progress/all` | ✅ | Score timeline |
| GET | `/analysis/{photo_id}/recommendations` | ✅ | Personalized recs |
| GET | `/plan` | ✅ | Active plan + milestones |
| POST | `/plan/checkin` | ✅ | Log check-in (streak) |
| GET | `/products/recommendations` | ✅ | Affiliate product recs |
| GET | `/products/category/{cat}` | ✅ | Browse category |
| GET | `/products/categories` | ✅ | List categories |
| GET | `/profile` | ✅ | Full profile |
| PUT | `/profile` | ✅ | Update fields |
| POST | `/profile/onboarding` | ✅ | Mark onboarding done |
| DELETE | `/profile/delete` | ✅ | GDPR delete |
| GET | `/progress/history` `/checkins` `/streak` `/milestones` `/photos/*` | ✅ | Engagement |
| POST | `/progress/checkin` `/progress/photos/upload` | ✅ | Check-in + photo |
| GET | `/dashboard` | ✅ | One-call home summary |
| GET | `/explore` | ✅ | Anonymised transformations + articles |

> Full routes: `backend/app/routes/*.py`. Response shapes: `backend/app/schemas.py`.

---

## 4. Missing credentials (blocking real features)

| Secret | Where | Needed for | Status |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | `.env` (local) + Render | Personalized plans (else fallback templates) | ✅ local (set in `.env`) / ⚠️ Render (set in env) |
| `CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET` | Render env | Image storage (else uploads fail) | ❌ missing |
| `STRIPE_SECRET_KEY` + webhook | n/a (route not built) | Paid subscriptions | ❌ missing + route missing |
| `SECRET_KEY` | Render env | JWT signing (currently default!) | ⚠️ must set |
| `DATABASE_URL` | Render env | Postgres (already live) | ✅ set |

---

## 5. Known gaps & tech debt (honest list)

1. **No Stripe/billing endpoint.** Subscription is frontend-only until `/payments/*` is built.
2. **Score may be heuristic/mock** when MediaPipe/PyTorch unavailable (Render 512MB OOM risk). Do not over-claim.
3. **`SECRET_KEY` default** in `config.py` — must be overridden in prod.
4. **Rate limiter is in-memory** (not Redis) — resets on restart, per-worker.
5. **CORS `*`** — fine for MVP, lock down before real traffic.
6. **`/upload/save` trusts the Cloudinary URL** — validated only by cloud-name substring. Harden later.
7. **Frontend is zero** — every UI decision is still open (see ROADMAP).

---

## 6. Next tasks (ordered)

1. ✅ Save `PSYCHOLOGY.md`, `ROADMAP.md`, `CONTEXT.md` (this task).
2. Scaffold Next.js + TypeScript + Tailwind in `frontend/`.
3. Implement auth (signup/login/me) + token handling per ROADMAP §7.
4. Implement upload → analysis → results (direct Cloudinary flow).
5. Implement dashboard + plan + streak/check-in.
6. Paywall (needs Stripe backend + frontend).
7. Landing page + SEO.
8. Request real credentials (DeepSeek, Cloudinary, Stripe) **only when the feature needs them**.

---

## 7. How to run locally

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real values
uvicorn app.main:app --reload --port 8000
# Swagger: http://localhost:8000/docs

# Frontend (once scaffolded)
cd frontend
npm install && npm run dev
# http://localhost:3000
```

