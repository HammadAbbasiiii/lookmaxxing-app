# LookMaxx — Web MVP Roadmap & Engineering Spec

> Build order: **landing → signup/login → upload → analysis → results → dashboard → plan → paywall → retention loops.**
> Every screen is spec'd against the **live** FastAPI backend (`https://lookmaxx-api.onrender.com/api/v1`).
> This file is written to be *brutal* on purpose — we fix problems here, not after launch.

---

## 0. Mission & North Star

**North Star metric:** % of new signups who upload a photo **and** return for a Day-2 check-in within 48h.

The product dies if a user signs up and never uploads (activation), or uploads and never returns (retention — startups lose ~77% of users in 3 days). Everything below is designed to beat those two failures.

---

## 1. Brutal multi-role review (read this before coding)

### 👨‍💼 Product Manager
- **The backend is ahead of the frontend.** We already have analysis, plans, products, progress, dashboard, explore endpoints. The risk is NOT "can we build features" — it's "will anyone stay".
- **One sharp wedge, not a platform.** V1 = *"Upload one photo, get a score + a 90-day plan + a streak."* Do not build settings, forums, or leaderboards in V1.
- **Kill-switch decision:** if DeepSeek key is missing, the backend silently serves template plans. That's fine for V1 — but we must **label nothing as "AI-powered" falsely** in a way that over-promises.

### 👨‍🔧 Frontend engineer (self-critical)
- **Do not call `/photos/upload` (multipart) from the browser for a 10MB HEIC** — we'd push megabytes through Render's single 512MB worker. Use the **direct Cloudinary flow** (`GET /upload/signature` → upload to Cloudinary → `POST /upload/save`) after client-side compression.
- **Auth token storage**: JWT in `localStorage` is easy but XSS-prone. Prefer an **httpOnly cookie** set via a tiny Next.js proxy, OR at minimum short-lived tokens + CSRF-safe patterns. Trade-off documented in §7.
- **State**: TanStack Query for all server state (built-in caching = fewer DeepSeek/DB calls = less cost). Never hand-roll `useEffect` fetch loops.
- **The score is the product.** It must render in <1s after analysis completes, in tabular numerals, with a count-up animation.

### 👨‍🔧 Backend engineer (self-critical)
- **Gap #1: there is no billing endpoint.** `User` has `is_subscribed`/`subscription_tier`/`subscription_customer_id`, but no Stripe route. The paywall is frontend-only until we add `/api/v1/payments/*`. See §10.
- **Gap #2: analysis may be heuristic.** If MediaPipe `face_landmarker.task` or PyTorch `RankInfoNet` is missing/OOM, the score is a **plausible mock**. We must not market it as clinical. (See `prediction_service._mock_score`, `face_analysis_service._heuristic_breakdown`.)
- **Gap #3: rate limiter is in-memory** (`rate_limit.py`) and resets per worker/restart. Acceptable for V1, but note it.
- **Cost**: DeepSeek is cached in Redis (24h TTL). Keep it that way — every uncached plan = money + latency.

### 📣 Marketing manager
- **Hook = "What's your score?"** The landing page must answer it in 3 seconds with one CTA: *"See your score — free."*
- **Loss aversion copy**: "Your streak (🔥 12 days) will reset tonight" beats "log in again".
- **Social proof**: real (anonymised) transformations from `/explore`, never fake before/afters.
- **No cringe.** The 16-year-old will screenshot anything embarrassing. Keep tone confident, not thirsty.

### 🧑 A 16-year-old consumer (the one who actually matters)
- "I'm not reading 400 words. Show me my score in 5 seconds or I'm gone."
- "Is it free? Don't make me put a card in to see my number."
- "Can I screenshot the score and send it to the group chat?" (→ shareable result card)
- "Don't lecture me. Give me 2-minute tasks I can actually do."
- "If it looks like a cheap scam app, I'm out." (→ black + gold, fast, no fake reviews)

---

## 2. Tech stack (chosen, with reasons)

### Frontend (NEW — nothing exists yet)
| Concern | Choice | Why |
|---|---|---|
| Framework | **Next.js 15 (App Router)** | SSR for SEO landing + client islands for app; one deploy on Vercel |
| Language | **TypeScript (strict)** | Catch API-shape drift against FastAPI schemas |
| Styling | **Tailwind CSS v4** | Speed + design tokens map 1:1 to PSYCHOLOGY.md |
| Server state | **TanStack Query v5** | Caching, retries, optimistic updates, fewer backend calls |
| Forms/validation | **react-hook-form + Zod** | Shared schemas mirror backend Pydantic models |
| Animation | **Framer Motion** | Count-up score, progress, transitions |
| Toasts | **sonner** | Non-blocking success/error feedback |
| Icons | **lucide-react** | Consistent, tree-shakeable |
| HTTP | **native fetch + query** | No axios needed |
| Deploy | **Vercel** (Hobby) | Free, global CDN, edge functions for `/api` proxy |

**Rejected**: SPA-only (CRA/Vite) — poor SEO for the landing page (organic traffic is our cheapest growth). React Native — out of scope (web-only MVP). Svelte/Vue — team velocity on React ecosystem is higher.

### Backend (EXISTS — do not rewrite)
FastAPI + SQLAlchemy + Postgres (Render) + Cloudinary + DeepSeek + Redis. Live at `https://lookmaxx-api.onrender.com/api/v1`.

### API proxy decision
The browser talks to `https://lookmaxx-api.onrender.com/api/v1` directly (CORS is already `allow_origins=["*"]`). For auth-cookie hardening + hiding keys, add a **Next.js route handler proxy** (`/api/*` → backend) in a later phase, not V1.

---

## 3. Page-by-page spec

Every screen lists: **purpose · key UI · copy · API · states to handle.**

### 3.1 Landing (`/`)
- **Purpose**: answer "What's your score?" in 3s, one CTA.
- **UI**: black hero, huge Space Grotesk headline *"What's your score?"*, gold CTA *"See your score — free"*, a blurred/looped "score reveal" teaser, 3 trust chips (Free · Private · 90-day plan), anonymised transformations strip.
- **Copy**: lead with the outcome, not the product. Subhead: *"Upload one photo. Get your baseline score and a 90-day plan to improve it."*
- **API**: none (marketing only). Optional: preload `/explore` transformations if public.
- **States**: mobile hero, reduced-motion fallback, no-JS SEO content.

### 3.2 Signup (`/signup`)
- **Purpose**: minimal friction; 3 fields max.
- **UI**: email, password, (optional) first name. Gold button *"Create account"*. Google/OAuth is a **later** phase (backend has no OAuth route yet — do not promise it).
- **Copy**: micro-commitment subtext *"Your score is private. Takes 60 seconds."*
- **API**: `POST /auth/signup` (JSON: `email`, `password`, `full_name`).
- **States**: see §9 for the full 20-scenario error matrix.

### 3.3 Login (`/login`)
- **API**: `POST /auth/login` (OAuth2 form-urlencoded: `username`=email, `password`). Store token (see §7).
- **Copy on error**: *"Incorrect email or password."* (never reveal which field was wrong — anti-enumeration).

### 3.4 Onboarding (`/onboarding`) — 3 micro-steps, skippable
1. Age + gender (drives gender-specific scoring). 2. Pick **one** primary goal (`improve_skin`, `jawline`, `confidence`, …). 3. "How serious are you?" (commitment lever).
- **API**: `PUT /profile` (age/gender/goals) then `POST /profile/onboarding`.
- **Copy**: *"Pick one goal. We'll build your plan around it."*
- **Rule**: every step has a **skip**; never trap a user in onboarding.

### 3.5 Upload (`/upload`)
- **Purpose**: get a usable front-facing selfie with least friction.
- **UI**: camera capture **or** file picker (`.jpg/.png/.heic`), live guide ("face the light, look straight"), 10MB cap indicator.
- **Client-side**: compress to ≤1200px JPEG ~75% **before** upload (mirrors backend `compress_for_upload`), then **direct Cloudinary flow**: `GET /upload/signature` → upload to Cloudinary → `POST /upload/save` → `POST /photos/analyze/{photo_id}`.
- **Copy**: *"Natural light, face forward, no filters."*
- **States**: unsupported type, >10MB, no camera permission, upload timeout, Cloudinary failure.

### 3.6 Analyzing (`/analyzing/{photo_id}`)
- **Purpose**: manage the ~5–10s wait without losing the user.
- **UI**: gold progress ring, rotating status copy (*"Finding your face…" → "Measuring symmetry…" → "Scoring skin…"*).
- **API**: poll `GET /photos/{id}` every 1.5s until `analysis_status` is `completed`/`failed`. **Stop polling** at 60s and show a retry (don't infinite-loop).
- **Copy**: status copy is the peak-end "build-up" — make the reveal feel earned.

### 3.7 Results (`/result/{photo_id}`)
- **Purpose**: THE moment. The score is the product.
- **UI**: giant animated score (tabular numerals, color-coded per scale), category bars (symmetry/skin/jawline/eyes/nose/lips), **strengths** (frame positively first) then **weaknesses** (one, actionable), face-shape label, shareable card, gold CTA *"Get my 90-day plan"*.
- **API**: `GET /analysis/{photo_id}`.
- **Copy**: headline like *"76 — Strong baseline. Here's your edge."* Weakness framed as *"Focus area: jawline definition (+2 potential)"*.
- **States**: `failed` (validation error → friendly retry), no-face detected, share-copy button.

### 3.8 Dashboard (`/app`)
- **Purpose**: one glance = "where am I + what's next". Use the single `/dashboard` call.
- **UI**: big current score (+ delta vs baseline), 🔥 streak chip, Day X/90 progress ring, next action card, 2-of-5 tasks today (Zeigarnik), next milestone teaser.
- **API**: `GET /dashboard`.
- **Copy**: next action from backend (`_get_next_action`): *"Apply Vitamin C serum (AM)"*.
- **States**: no plan yet → primary CTA *"Upload your first photo"*; streak-about-to-expire warning.

### 3.9 Plan / Today (`/plan`)
- **Purpose**: daily 2-minute tasks, no wall of text.
- **UI**: today's tasks as checkboxes, mark done → streak bump; week timeline; phase label (Phase 1/2/3).
- **API**: `GET /plan` + `POST /plan/checkin` (or `POST /progress/checkin`).
- **Copy**: *"Day 12/90 — stay consistent to build lasting habits."*

### 3.10 Progress (`/progress`)
- **Purpose**: Peak-End — show them changing.
- **UI**: score-over-time line chart (tabular), **before/after slider** (baseline vs latest), milestones timeline.
- **API**: `GET /analysis/progress/all` + `GET /progress/photos/compare`.
- **States**: fewer than 2 photos → *"Take your next progress photo at Day 30."*

### 3.11 Explore (`/explore`)
- **Purpose**: social proof + education (keeps them engaged, not just scored).
- **UI**: anonymised transformation cards ("Alex: 71 → 84"), article cards.
- **API**: `GET /explore`.
- **States**: empty transformations → show articles only (never fake data).

### 3.12 Products (`/products`)
- **Purpose**: secondary monetization (affiliate) *after* value is established.
- **UI**: "Because your weakest areas are skin & jawline…" → product grid with budget filter (budget/mid/premium).
- **API**: `GET /products/recommendations?tier=…` + `/products/categories`.
- **Disclosure**: "We may earn a commission" (transparency = trust).

### 3.13 Paywall (`/upgrade`)
- **Purpose**: convert hooked users. 3 tiers (Free/Pro/Elite), Pro highlighted, annual toggle with anchor price.
- **API**: **none yet** — needs `POST /payments/create-checkout` (Stripe) to be built in backend first. Until then, show a "coming soon / join waitlist" state — **do not fake a live checkout.**
- **Copy**: loss framing + risk reversal: *"Keep your streak & history synced. Cancel anytime."*

### 3.14 Settings / Profile (`/settings`)
- **UI**: edit profile, delete account (GDPR), sign out. Minimal.
- **API**: `GET/PUT /profile`, `DELETE /profile/delete`.

---

## 4. API contract map (frontend ↔ backend)

| Frontend action | Backend call(s) |
|---|---|
| Signup | `POST /auth/signup` |
| Login | `POST /auth/login` → store token |
| Load me | `GET /auth/me` (validate token on boot) |
| Onboarding | `PUT /profile` + `POST /profile/onboarding` |
| Upload | `GET /upload/signature` → Cloudinary → `POST /upload/save` → `POST /photos/analyze/{id}` |
| Poll analysis | `GET /photos/{id}` (1.5s interval, 60s cap) |
| Show result | `GET /analysis/{photo_id}` |
| Dashboard | `GET /dashboard` |
| Plan/tasks | `GET /plan` + `POST /plan/checkin` |
| Progress | `GET /analysis/progress/all` + `GET /progress/photos/compare` |
| Explore | `GET /explore` |
| Products | `GET /products/recommendations?tier=` |
| Upgrade | `POST /payments/create-checkout` (**to build**) |

---

## 5. Frontend component inventory (to scaffold)

- `ui/Button`, `Input`, `Card`, `Badge`, `ProgressRing`, `ScoreMeter`, `Skeleton`, `Toast` (sonner), `Dialog`.
- `Score` (tabular count-up), `CategoryBar`, `StreakFlame`, `BeforeAfterSlider`, `MilestoneTimeline`, `TransformCard`.
- `layout/AppShell` (top nav + bottom tab nav on mobile: Dashboard / Plan / Progress / Explore / Settings).

---

## 6. State & data strategy

- **TanStack Query** for all server state. Keys: `['me']`, `['dashboard']`, `['plan']`, `['analysis', id]`, `['progress']`, `['explore']`, `['products', tier]`.
- `staleTime`: dashboard/plan 30s, analysis 60s, explore 5min, products 5min → fewer backend hits = lower cost.
- Auth token in a query-agnostic store (see §7). Redirect logic via a `useRequireAuth` hook + route guard.
- No Redux. No global state beyond auth + a tiny UI store (zustand, optional).

---

## 7. Auth & token storage (trade-off, decided)

**Decision for V1**: store JWT in **`localStorage`** + attach `Authorization: Bearer` header, with a documented migration path to **httpOnly cookie** via a Next.js `/api/*` proxy in Phase 2.

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| localStorage | Simple, works with CORS `*` today | XSS reads token | ✅ V1 (mitigate: CSP, no 3rd-party scripts) |
| httpOnly cookie + proxy | XSS-safe | Needs proxy route, CSRF handling, CORS creds | Phase 2 |

**Mitigations for V1**: strict Content-Security-Policy, no inline 3rd-party JS, sanitize user input, keep token TTL short (backend default 30min — consider a refresh flow later). Never log tokens.

---

## 8. Upload flow (final, performance-first)

1. User picks/captures image.
2. Client compresses (canvas/`browser-image-compression`): max 1200px, JPEG ~75%.
3. `GET /upload/signature` (authenticated) → `{signature, timestamp, cloud_name, api_key, folder, public_id}`.
4. `POST` image directly to Cloudinary (`https://api.cloudinary.com/v1_1/{cloud_name}/image/upload`) with the signed fields.
5. `POST /upload/save` (`file_url`, `public_id`) → `{photo_id}`.
6. `POST /photos/analyze/{photo_id}` → starts background analysis.
7. Navigate to `/analyzing/{photo_id}` and poll.

> Rationale: never send raw bytes through the 512MB Render worker. Compression + direct upload keeps it fast and cheap.

## 9. Signup & login — 20 scenarios (test every one)

The frontend validates **first** (Zod), the backend validates **second** (Pydantic). Both must agree. Here are the 20 cases to build and test:

| # | Scenario | Expected behavior | Copy / note |
|---|---|---|---|
| 1 | Valid signup (email + password + name) | 201, then redirect to onboarding | *"Account created."* |
| 2 | Duplicate email | Backend 400 `Email already registered` | Show *"That email is already registered. Log in instead."* + login link |
| 3 | Email with leading/trailing spaces | Backend trims → succeeds | Client also trims before send (defense in depth) |
| 4 | Email in mixed case (`Foo@Bar.com`) | Backend lowercases → treated as same account | Do NOT create a duplicate |
| 5 | Invalid email (no `@`, no TLD) | Zod blocks → 422 if it reaches backend | *"Enter a valid email address."* |
| 6 | Password < 6 chars | Zod blocks → backend 422 | *"Password must be at least 6 characters."* |
| 7 | Empty email or password | Zod blocks on blur/submit | *"Email is required."* / *"Password is required."* |
| 8 | Password of only spaces | `.strip()` → empty → reject | *"Password can't be empty."* |
| 9 | Email longer than 254 chars | Client `maxLength={254}` | Prevent DB `VARCHAR(255)` overflow |
| 10 | Signup with existing email, different case | Same as #4 — must not create duplicate | Backend lowercases on both signup & login |
| 11 | Network down / DNS fail | No response → timeout | *"Can't reach the server. Check your connection and try again."* |
| 12 | Rate limited | Backend 429 | *"Too many attempts. Wait a minute and try again."* |
| 13 | Server 500 | Global handler returns friendly 500 | *"Something went wrong on our end. Please try again."* (never show raw detail) |
| 14 | Signup succeeds but auto-login fails | Fallback to `/login` with email prefilled | Toast: *"Account created — log in to continue."* |
| 15 | Password manager autofill/paste | Must work — **never block paste** | Use `autocomplete="new-password"` / `"current-password"` |
| 16 | Mobile keyboard | Correct `type` + `inputMode` | `type="email"`, `inputMode="email"`, `enterKeyHint="go"` |
| 17 | Internationalized email (Unicode local part) | Backend `EmailStr` accepts | Client must not over-reject |
| 18 | Obvious typo domain (`gmal.com`) | Optional inline warning (Phase 2) | *"Did you mean gmail.com?"* |
| 19 | Double-tap Submit (rapid clicks) | Disable button while pending; dedupe | `isSubmitting` guard in react-hook-form |
| 20 | Login: wrong password **or** wrong email | Identical generic message (anti-enumeration) | *"Incorrect email or password."* |

**Additional auth rules**
- After login, store token, then `GET /auth/me` to hydrate the session and verify token validity.
- On 401 from any authed call, clear token and redirect to `/login` (token expired / invalid).
- Logout = discard token (backend `/auth/logout` is a no-op).

---

## 10. Error message catalog (exact copy)

Every error gets: **status code → user-facing toast/inline copy → next action.** No raw exception text ever reaches the user.

| Trigger | Status | User copy | Next action |
|---|---|---|---|
| Duplicate email | 400 | *"That email is already registered."* | Link to login |
| Invalid Cloudinary URL on save | 400 | *"Upload failed. Please try again."* | Re-upload |
| Invalid product category/tier | 400 | *"That filter isn't available."* | Reset filter |
| Empty profile update | 400 | *"No changes to save."* | — |
| Unauthorized (expired/bad token) | 401 | *"Session expired. Please log in again."* | Redirect `/login` |
| Photo not found / not yours | 404 | *"Photo not found."* | Back to dashboard |
| No analysis yet | 404 | *"This photo hasn't been analyzed yet."* | Retry analysis |
| No plan found | 404 | *"Upload and analyze a photo to get your plan."* | CTA to upload |
| File too large | 413 | *"That photo is too big. Max 10MB."* | Re-pick smaller |
| Unsupported file type | 400 | *"Use a JPG, PNG, or HEIC file."* | Re-pick |
| Validation failed (unusable image) | 400 | *"We couldn't find a clear face. Try better lighting, facing forward."* | Retry upload |
| Rate limit | 429 | *"Too many requests. Wait a moment."* | Auto-retry after backoff |
| Server error | 500 | *"Something went wrong. Please try again."* | Retry |
| Network / offline | — | *"No connection. Check your signal."* | Retry on reconnect |
| Upload timeout | — | *"Upload is taking too long. Try a smaller photo."* | Retry |
| Cloudinary failure | 500 | *"Image upload failed. Try again."* | Retry |
| Analysis `failed` status | — | *"Analysis couldn't complete. Try a clearer photo."* | Retry / re-upload |
| Analysis timeout (>60s poll) | — | *"Still working… give it a moment, or retry."* | Retry poll |
| DeepSeek fallback (not an error) | — | *(silent)* — serve template plan | Do NOT tell user it's "fake"; just deliver value |

**Rules**
1. Errors are **inline + toast**, never a blank red screen.
2. Every error has a **recovery action** (retry / back / fix input).
3. Show field errors **under the field**, not only in a toast.
4. `401` always clears the session and redirects.
5. Loading, empty, and error states are designed — never an afterthought.

## 11. Loading & empty states (designed, not afterthoughts)

| Screen | Loading | Empty | Error |
|---|---|---|---|
| Dashboard | Skeleton cards | "Upload your first photo" CTA | Retry card |
| Plan | Skeleton task list | "No active plan — analyze a photo" | Retry |
| Progress | Chart skeleton | "No photos yet" | Retry |
| Explore | Card skeletons | "Articles coming soon" (never fake transformations) | Retry |
| Products | Grid skeletons | "No recommendations yet — analyze first" | Retry |
| Analysis | Progress ring + rotating copy | — | Friendly retry |

**Rules**: skeletons match final layout (no layout shift); empty states always include a next action; loading never blocks navigation.

---

## 12. Monetization — Stripe plan (backend gap, to build)

**Tiers**: Free (1 analysis + streak) / **Pro $9.99/mo** (unlimited analyses + full plan + check-ins) / **Elite $19.99/mo** (decoy — adds 1:1 "coach" Q&A + priority). Annual toggle = anchor (show "save 58%").

**Backend endpoints to add** (does not exist yet — see `CONTEXT.md`):
1. `POST /payments/create-checkout` → creates Stripe Checkout Session, returns URL.
2. `POST /payments/portal` → Stripe Customer Portal (manage/cancel).
3. `POST /payments/webhook` → verify signature, set `User.is_subscribed` / `subscription_tier` / `subscription_customer_id` / `subscription_end`.
4. `GET /payments/status` → current tier + expiry (or reuse `GET /profile`).

**Frontend**: `/upgrade` renders tiers, calls `create-checkout`, redirects to Stripe, polls `/payments/status` on return. **Until backend route exists, `/upgrade` shows "join waitlist" — never a fake checkout.**

**Free-tier enforcement**: the backend must actually gate analyses by `subscription_tier` (currently it does NOT). Add a `require_pro` dependency on the second+ analysis. This is the real monetization work, not the UI.

---

## 13. Performance & cost budget (founder lens)

**Frontend**
- LCP < 2.5s on 4G; landing page < 150KB JS gzipped (code-split the app behind `/app`).
- Images: Cloudinary `f_auto,q_auto` + `next/image`; never ship a >200KB hero.
- Fonts via `next/font` (self-hosted, subset). No layout shift.

**Backend (already optimized — respect it)**
- Render **starter 512MB**, 1 worker. **Never** add boot-time heavy imports (PyTorch/MediaPipe are lazy-loaded — keep it that way).
- DeepSeek cached in Redis 24h → **every uncached plan = money + latency**. Client `staleTime` also reduces repeat calls.
- Health endpoint stays lightweight (it keeps the free worker warm).

**Token/API cost discipline**
- DeepSeek: cache-key by `score|gender|weakest` (already in `deepseek_service`). Do not regenerate plans for identical inputs.
- Cloudinary: compress client-side + `q_auto` → smaller storage/bandwidth.
- No redundant polling: analysis poll = 1.5s interval, hard 60s cap; stop on `completed`/`failed`.

**Run-cost target**: stay within Render + Vercel + Cloudinary + Redis free tiers for the MVP (≈ $0/mo). Add paid tiers only when usage justifies it.

---

## 14. Testing plan (prove it, don't hope it)

- **Unit (Vitest)**: Zod schemas match backend Pydantic; score color mapping; copy helpers; auth-store logic; the 20 signup validators.
- **Component (React Testing Library)**: Button loading states, Score count-up, empty/error states, Paywall tier selection.
- **E2E (Playwright)**: happy path (signup → onboarding → upload → analyze → result → dashboard); duplicate email; wrong password; expired token redirect; 429 handling; upload >10MB; invalid file; network-offline.
- **Backend already has** `tests/` (auth, plan, photos, validation, database) — run `pytest` before touching API.
- **Manual checklist**: the 20 scenarios in §9 + every row in §10 + §11 states.

**CI**: on push → `pytest` (backend) + `tsc --noEmit` + `vitest` + `playwright` (smoke). Fail the build on any regression.

---

## 15. Security checklist (V1 minimum)

- [ ] Set real `SECRET_KEY` in Render (currently defaults in code — critical).
- [ ] CSP header; no third-party scripts except Cloudinary/Stripe.
- [ ] Sanitize all user-rendered strings (React escapes by default — don't use `dangerouslySetInnerHTML`).
- [ ] Never log tokens, emails in query strings, or passwords.
- [ ] Lock CORS to the Vercel domain before real traffic (currently `*`).
- [ ] 16+ age gate + non-medical disclaimer on results.
- [ ] HTTPS only (Render/Vercel provide it).
- [ ] Hard rate-limit on `/auth/*` and `/payments/*` (in-memory limiter is V1-only; move to Redis later).

---

## 16. Delivery milestones

| Phase | Scope | Exit criteria |
|---|---|---|
| **0 — Docs** | `PSYCHOLOGY.md`, `ROADMAP.md`, `CONTEXT.md` | ✅ (this task) |
| **1 — Scaffold** | Next.js + TS + Tailwind + fonts + design tokens + AppShell | `npm run dev` renders dark shell |
| **2 — Auth** | Signup/login/me, token store, guards, 20 scenarios | All 20 scenarios pass E2E |
| **3 — Core loop** | Upload → analyze → result → dashboard → plan | Happy path E2E green |
| **4 — Retention** | Streak, check-in, progress, explore | D2-return instrumentation wired |
| **5 — Monetize** | Stripe backend + `/upgrade` + gating | Test checkout → webhook → tier flips |
| **6 — Launch** | Landing SEO, analytics, error tracking | LCP < 2.5s, error rate < 1% |

---

## 17. Definition of Done (every feature)

1. Works on mobile **and** desktop.
2. Has loading, empty, **and** error states (with recovery action).
3. All error copy matches §10.
4. No raw API errors surface to the user.
5. Accessible (keyboard, contrast, `aria-label`, reduced-motion).
6. Backed by a unit/E2E test where behavior is non-trivial.
7. Does not regress the North Star (activation / D2 retention).
8. Costs nothing extra in tokens/bandwidth that could've been cached.

> **If it doesn't make the 16-year-old's first 5 minutes faster or more compelling, it doesn't ship in V1.**




