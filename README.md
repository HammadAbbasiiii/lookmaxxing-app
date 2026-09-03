# LookMaxx — AI Facial Analysis & 90-Day Transformation (Web)

> **Your face, scored. Your potential, planned.** Upload one photo → get a baseline score, a personalized 90-day action plan, streaks, and before/after progress. Private by default. Free to start.

![License: MIT](https://img.shields.io/badge/license-MIT-gold) ![Backend: FastAPI](https://img.shields.io/badge/backend-FastAPI-009688) ![Frontend: Next.js 15](https://img.shields.io/badge/frontend-Next.js%2015-black) ![Deploy: Render + Vercel](https://img.shields.io/badge/deploy-Render%20%2B%20Vercel-blue)

LookMaxx is a browser-based web app that quantifies facial aesthetics and turns the result into a **90-day self-improvement plan**. No app store, no download — a user shares one front-facing photo and gets, in seconds, an overall score (clamped 30–95), a per-feature breakdown, an achievable "potential" score, and a phased plan with daily 2-minute tasks, streaks, and milestones.

## ✨ Features

- **Instant score** — overall 0–100 (clamped 30–95) + per-feature scores (symmetry, skin, jawline, eyes, nose, lips).
- **Potential score & improvement gap** — motivates without shaming.
- **Personalized 90-day plan** — Phase 1/2/3, daily tasks, weekly timeline (DeepSeek AI with deterministic fallback).
- **Engagement engine** — streaks, milestone celebrations (Day 7/14/21/30/45/60/75/90), before/after slider, anonymized transformations.
- **Affiliate product recommendations** targeted at your weakest features.
- **Premium tiers** — Free / **Pro $9.99/mo** / Elite $19.99/mo, with **server-authoritative gating** (no Inspect-Element bypass).

## 🏗 Architecture

```
Browser (Next.js 15)  ──HTTP/JSON──▶  FastAPI backend (Render)
   │ TanStack Query, Zod, Tailwind        │ JWT auth, SQLAlchemy
   │ (image bytes, direct upload)         │ ML face analysis (lazy)
   ▼                                       ▼
Cloudinary (signed)                  Postgres · DeepSeek · Redis
```

| Layer | Stack |
|---|---|
| Frontend | Next.js 15 (App Router) · TypeScript (strict) · Tailwind CSS v4 · TanStack Query v5 · react-hook-form + Zod · Framer Motion · sonner · lucide-react |
| Backend | FastAPI · SQLAlchemy · Postgres · Cloudinary · DeepSeek · Redis (rate limit) |
| Infra | Render (API) · Vercel (web) · Cloudinary (images) |

## 🔒 Security highlights

- **Server-authoritative premium gating** — the browser (and DevTools/Inspect Element) is treated as untrusted. Entitlements are read from the DB on every request via a `require_pro` dependency; the JWT carries only the user id, so editing localStorage or unhiding a button cannot unlock Pro.
- **Payments** — Stripe Checkout (server-created session) + **signed webhook** is the *only* writer of subscription state; the client never mutates entitlements.
- **Auth** — bcrypt password hashing, HS256 JWT (30-min TTL), anti-enumeration login, email normalization.
- **Abuse** — Redis-backed sliding-window rate limiting with in-memory fallback.
- **XSS/CSRF** — strict CSP, zero third-party scripts, React text-node rendering (no `dangerouslySetInnerHTML` on user/AI text).
- **Never crashes on bad data** — every response is decoded through Zod with safe fallbacks; every error has a recovery action (see `PRODUCT_SPEC.md` §9).
- **Privacy/GDPR** — private-by-default photos, explicit consent capture, one-tap account deletion, sub-processor DPAs, DPIA, and data-subject rights (full plan in `PRODUCT_SPEC.md` §20).

## ⚙️ Production hardening

Multi-layer caching (CDN → edge → Redis → TanStack Query), stateless horizontal scaling with health checks, structured logging + Sentry (PII scrubbed), Postgres backups, CI/CD with preview deploys, and per-environment secret rotation — specced in `PRODUCT_SPEC.md` §21.

## 🚀 Quick start

```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in real values
uvicorn app.main:app --reload   # http://localhost:8000/docs

# Frontend (Next.js)
cd frontend
npm install
cp .env.example .env.local      # NEXT_PUBLIC_API_URL=https://lookmaxx-api.onrender.com/api/v1
npm run dev                     # http://localhost:3000
```

## 📁 Project structure

```
lookmaxx-web/
├── PRODUCT_SPEC.md     # ⭐ master whole-product design spec (screens, security, psychology, monetization)
├── PSYCHOLOGY.md       # conversion/design psychology tokens
├── ROADMAP.md          # MVP checklist (14 screens, 20 signup scenarios, error catalog)
├── CONTEXT.md          # backend ground truth + credentials + gaps
├── MEMORY.md           # session snapshot for the coding agent
├── docs/               # legal: privacy policy, terms of service, DPIA
├── backend/            # FastAPI AI engine (live on Render)
└── frontend/           # Next.js web app (greenfield — spec complete)
```

## 📖 Documentation

The **master specification** is [`PRODUCT_SPEC.md`](./PRODUCT_SPEC.md) — it covers every screen, button, input, error, loading/empty state, the full security model, engagement/psychology engine, monetization/gating, performance budgets, testing matrix, GDPR/privacy compliance, production operations, and run/deploy guide. Companion docs: `PSYCHOLOGY.md`, `ROADMAP.md`, `CONTEXT.md`, `MEMORY.md`. Legal drafts (`PRIVACY_POLICY.md`, `TERMS_OF_SERVICE.md`, `DPIA.md`) live in `docs/`.

## ✅ Status

- **Backend:** ✅ live at `https://lookmaxx-api.onrender.com/api/v1` (FastAPI + Swagger).
- **Frontend:** 🟡 greenfield — full design spec complete; implementation next.

## 🧪 Testing

```bash
cd backend && pytest
```

## 📄 License

[MIT](./LICENSE)

---

*Built to be presented: clean architecture, a written product spec, tested backend, and a security model that treats the client as untrusted.*
