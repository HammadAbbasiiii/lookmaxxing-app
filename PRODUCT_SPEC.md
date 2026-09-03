# LookMaxx — Whole Product Design Specification (PDS)

> **Status:** ✅ Authoritative master spec — read this before writing any frontend code.
> **Scope:** the entire web product — every screen, button, input, error, loading/empty state, security, psychology, engagement, monetization, privacy/GDPR, production operations, performance, scalability, and GitHub/run readiness.
> **Companion docs:** `PSYCHOLOGY.md` (visual tokens + persuasion), `ROADMAP.md` (MVP checklist), `CONTEXT.md` (backend ground truth), `MEMORY.md` (session snapshot).
> **Where this doc wins:** if PSYCHOLOGY/ROADMAP/CONTEXT disagree, **this file is the tie-breaker.**

---

## 0. Document control

| Field | Value |
|---|---|
| Product | LookMaxx (web) |
| Version | 1.1 |
| Owner | Founder / solo builder |
| Backend | ✅ Live at `https://lookmaxx-api.onrender.com/api/v1` (commit `56915f9`) |
| Frontend | 🟡 Greenfield (`frontend/.gitkeep` only) |
| Target | Web MVP → Vercel (free tier) |

**How to read this file**
1. §1–§5 define *what* we're building and *why* (do not skip §5 Security).
2. §8 is the screen-by-screen contract — one section per screen, always in the order: **Purpose · Layout · Buttons · Inputs · States · Errors · Copy · Animation · API.**
3. §9 is the never-crash message rulebook + the full error catalog.
4. §18 is how to run/deploy and present this repo for a job application.
5. §20 is GDPR/privacy compliance (you process **biometric face data**) and §21 is the production/ops playbook (caching, load balancing, observability).

---

## 1. Executive summary

LookMaxx answers one question in under 3 seconds: **"What's my score?"** A user uploads a single front-facing photo and within seconds gets:

1. An **overall face score** (clamped 30–95) plus per-feature scores (symmetry, skin, jawline, eyes, nose, lips).
2. A **potential score** (what's achievable) and an **improvement gap** that motivates without shaming.
3. A **personalized 90-day action plan** (Phase 1 → 2 → 3) with daily tasks.
4. **Streaks, milestones, and before/after progress** to keep them coming back.
5. **Affiliate product recommendations** targeted at their weakest features.

**Monetization:** Free tier = 1 analysis + streak tracking. **Pro $9.99/mo** = unlimited analyses + full plan + check-ins. **Elite $19.99/mo** = decoy tier (1:1 coach Q&A + priority). Annual toggle anchors "save 58%".

**The promise we can actually keep (honesty is a feature):**
> *"Upload one photo. Get your baseline score and a 90-day plan to improve it. Private. Free to start."*

**What we will NOT do:** fake before/after photos, fabricated reviews, score inflation, or a checkout button that doesn't actually charge. The target audience flees from anything that "looks like a cheap scam app" — trust is the whole brand.

---

## 2. Product principles (non-negotiables)

These are the rules every screen and every line of code must obey. Violating any of them is a bug, not a decision.

1. **The app must never crash on bad data.** No message from the backend — missing field, `null`, string where a number is expected, HTML in a string, a 500, a timeout, a network drop — may ever produce a blank screen or an unhandled exception. (§9)
2. **Server-authoritative gating.** The browser is untrusted. Premium access is decided by the *backend*, never by the frontend, localStorage, or hidden UI. (§5)
3. **Every error has a recovery action.** A user can always *retry / go back / fix the input*. Never a dead-end red screen.
4. **Loading, empty, and error states are designed first**, not tacked on. Skeletons match final layout (zero layout shift); empty states always include the next action.
5. **Lead with the outcome, not the product.** Copy sells the *result* ("get your score", "see your transformation"), not the technology.
6. **Never shame, always coach.** Score language is neutral-to-encouraging. A low score is framed as *room to improve*, never *you're ugly*.
7. **Never fake.** No fake transformations, no fake reviews, no fake scarcity ("only 2 left"). Fake anything = instant churn.
8. **Never trap a user.** Onboarding is skippable; paywalls are dismissible; account deletion is one tap away (GDPR).
9. **Fast feels premium.** Target LCP < 2.5s on 4G; landing page < 150 KB JS gzipped; images auto-optimized via Cloudinary.
10. **Privacy is sacred.** Faces are sensitive biometrics. Photos are private by default; Explore only shows *anonymized* transformations.

---

## 3. Target audience & psychology foundation

### 3.1 Who we serve
- **Primary:** men 16–30, plus a growing women's segment 18–30. Self-improvement ("looksmaxxing"), grooming, and fitness adjacent.
- **Secondary:** men 30–45 returning to fitness/dating; skincare-curious users of any gender.
- **Device:** mobile-first (70%+ traffic from phone), desktop fully supported.

### 3.2 Core drivers (what they actually feel)
- **Aspiration** — "I can look noticeably better." The score + potential score *quantifies* hope.
- **Identity** — "I'm the kind of person who works on himself." Streaks and check-ins let them *be* that person.
- **Progress visibility** — "I'm changing and I can prove it." The before/after slider is the strongest retention asset.
- **Status / social proof** — "People like me improved." Anonymized transformations and milestone language ("top 20% of users") tap this.

### 3.3 Core fears (what makes them leave)
- **Shame** — a harsh low score → instant uninstall. → Neutral score labels + improvement framing.
- **Scam** — anything that looks cheap, fake, or pushy → instant distrust. → Black + gold premium palette, fast UI, no fake reviews, honest affiliate disclosure.
- **Privacy** — "will my face leak?" → Private-by-default photos, GDPR delete, no social login requirement, anonymized Explore.
- **Wasted effort** — "will this even work?" → 2-minute daily tasks, visible progress, risk-reversal copy.

### 3.4 Age-group vocabulary that lands (copy bank)
| Emotion | Words that work | Words that DON'T |
|---|---|---|
| Motivation | "lock in", "level up", "baseline", "build", "consistency", "momentum", "routine" | "obligation", "homework", "fix yourself" |
| Progress | "Day X/90", "streak", "milestone", "you're up +X pts" | "compliance", "adherence" |
| Achievement | "you're not most people", "top 20%", "transformation" | "congratulations on your compliance" |
| Risk (paywall) | "don't lose your streak", "keep your history", "cancel anytime" | "subscribe now or else" |
| Trust | "private", "free to start", "takes 60 seconds", "no card required" | "limited time!", "act fast!" |

> Full visual + persuasion tokens live in `PSYCHOLOGY.md`; §6 and §11 below operationalize them per screen.

---

## 4. System architecture

### 4.1 High-level diagram

```
┌────────────────────────────┐        ┌──────────────────────────────┐
│  Browser (Next.js 15)      │        │  Backend (FastAPI, Render)    │
│  ─ App Router, React       │  HTTP  │  ─ /api/v1/*                  │
│  ─ TanStack Query (cache)  │ ─────▶ │  ─ JWT auth, SQLAlchemy       │
│  ─ react-hook-form + Zod   │ JSON   │  ─ ML face analysis (lazy)     │
│  ─ Tailwind + Framer Motion│        │  ─ 90-day plan generator       │
└────────────┬───────────────┘        └──────┬──────────┬────────────┘
             │  image bytes (direct upload)  │          │
             ▼                                ▼          ▼
      ┌──────────────┐               ┌──────────┐  ┌──────────────┐
      │  Cloudinary  │               │ Postgres │  │ DeepSeek AI  │
      │  (signed)    │               │ (Render) │  │ (fallback ok)│
      └──────────────┘               └──────────┘  └──────────────┘
                                             │
                                      ┌──────┴──────┐
                                      │ Redis (rate │
                                      │ limit, opt) │
                                      └─────────────┘
```

### 4.2 Frontend stack (LOCKED)
| Concern | Choice | Why |
|---|---|---|
| Framework | **Next.js 15 (App Router)** | SSR/SEO landing + client islands for the app; one Vercel deploy |
| Language | **TypeScript (strict)** | Catch API-shape drift against FastAPI/Pydantic schemas |
| Styling | **Tailwind CSS v4** | Tokens map 1:1 to the design system (§6) |
| Server state | **TanStack Query v5** | Caching, retries, dedupe, optimistic updates, fewer calls |
| Forms/validation | **react-hook-form + Zod** | Zod schemas mirror backend Pydantic models |
| Animation | **Framer Motion** | Score count-up, progress rings, transitions |
| Toasts | **sonner** | Non-blocking success/error feedback |
| Icons | **lucide-react** | Consistent, tree-shakeable |
| HTTP | native `fetch` via a typed API client | No axios needed |
| Deploy | **Vercel** (Hobby) | Free, global CDN |

**Rejected:** SPA-only (poor SEO for landing), React Native (web-only MVP), Svelte/Vue (React velocity).

### 4.3 Backend (EXISTS — do not rewrite)
FastAPI + SQLAlchemy + Postgres (Render) + Cloudinary + DeepSeek + Redis (optional). ML model (PyTorch `rank_info_net_full.pth`, 94 MB) is **lazy-loaded** — never import at boot (512 MB worker constraint). If ML/DeepSeek is unavailable the backend serves a **deterministic heuristic/fallback** — this is intentional resilience, not a bug.

### 4.4 Data flow (the critical path — upload → result)
1. User picks/captures image → client compresses to ≤1200px JPEG ~75% (`browser-image-compression`).
2. `GET /upload/signature` (authenticated) → signed Cloudinary params.
3. Client `POST`s the image **directly to Cloudinary** (never through the 512 MB worker).
4. `POST /upload/save` (`file_url`, `public_id`) → creates the `Photo`, returns `photo_id`.
5. `POST /photos/analyze/{photo_id}` → background analysis starts.
6. Client navigates to `/analyzing/{photo_id}` and polls `GET /photos/{id}` (1.5 s interval, 60 s cap).
7. On `analysis_status == completed` → render `/results/{photo_id}`.

**Fallback path (also supported):** `POST /photos/upload` multipart → server compresses + uploads to Cloudinary + runs background analysis. Both paths exist; the **direct Cloudinary path is preferred** for speed/cost.

### 4.5 API proxy decision
V1: browser talks to `https://lookmaxx-api.onrender.com/api/v1` directly (CORS `*` today). Phase 2: add a Next.js route-handler proxy (`/api/*` → backend) to move auth to an **httpOnly cookie** and hide the backend origin.

---

## 5. Security architecture (server-authoritative)

> **One sentence summary:** the browser — including DevTools, Inspect Element, and the console — is an *untrusted client*. Every premium/paid entitlement is decided and enforced **on the server**, and the frontend merely *reflects* what the server says.

### 5.1 Threat model
| Attacker | Goal | Vector |
|---|---|---|
| Curious user | Unlock Pro free | Inspect Element, edit localStorage, unhide buttons, direct `fetch` to the API |
| Script-kiddie | Abuse / spam | Replay requests, brute-force login, upload junk |
| Malicious site / XSS | Steal JWT | Inject script that reads `localStorage` token |
| Competitor / bot | Scrape data | Hammer public endpoints, scrape Explore |
| Insider/leak | Expose secrets | Git history, committed `.env` |

### 5.2 The Inspect-Element truth (read this first)

**A user CANNOT get premium features just by editing the frontend — *if and only if* the backend gates them.** Concretely, a user can:

1. Open Inspect Element → change `localStorage.subscription_tier = "pro"`. → **Useless** if the UI never trusts localStorage for gating and the backend re-checks the DB on every request.
2. Delete a `hidden` class or `disabled` attribute to reveal a "Pro" button. → **Useless** if clicking it still hits a backend endpoint that returns `403 Forbidden` for free users.
3. Open the Network tab, copy the `Authorization: Bearer` header, and call the API directly with cURL/Postman. → **Useless** if the backend checks `subscription_tier` server-side.
4. Edit the JWT payload in the browser to add `"tier":"pro"`. → **Impossible** — the token is HS256-signed with a server-only `SECRET_KEY`; tampering breaks the signature and the server rejects it (`JWTError` → 401).

**Therefore:** the frontend shows/hides premium UI only as a *polish* (good UX), never as a *security boundary*. The real boundary is a backend `require_pro` dependency. **This dependency does NOT exist yet** — it is the #1 monetization-security task (§12).

### 5.3 The gating pattern (frontend + backend contract)

```text
Frontend (polish only, NOT security):
  - reads current_user.subscription_tier from GET /auth/me or GET /profile
  - hides Pro-only buttons, shows a lock, deep-links to /upgrade

Backend (the REAL gate):
  def require_pro(current_user = Depends(get_current_user)):
      if not current_user.is_subscribed or current_user.subscription_tier not in ("pro","elite"):
          raise HTTPException(403, "Upgrade to Pro to unlock this feature")
      return current_user

  # applied to: POST /photos/analyze/* (2nd+ analysis), POST /plan/checkin, GET /analysis/{id}/plan
```

**Invariant:** the backend must read `subscription_tier` **from the DB on every request** (via `get_current_user`), never from a client-sent field. The JWT carries only `sub` (user id) + `exp` — no entitlements — so entitlements can only come from the DB.

### 5.4 Auth & token handling
- **Password hashing:** bcrypt (passlib). Minimum 6 chars today; raise to 8 + a strength meter in Phase 2.
- **JWT:** HS256, 30-minute expiry, payload = `{sub: user_id, exp}`. Signed with `SECRET_KEY`.
- **Anti-enumeration:** login returns the same `401 "Incorrect email or password"` whether the email exists or the password is wrong. Never reveal which.
- **Email normalization:** trim + lowercase on both signup and login (prevents duplicate accounts via `Foo@Bar.com`).
- **Token storage (V1):** `localStorage` + `Authorization: Bearer` header. Mitigations: strict CSP, zero third-party scripts, short TTL. **Phase 2:** move to httpOnly cookie via the Next.js proxy (XSS-safe) — this is the documented migration path.
- **401 handling:** on any `401`, the client **immediately clears the token and redirects to `/login`** (with a safe `?next=` that is validated against an allowlist, never an open redirect).

### 5.5 Payment security (Stripe — the "money" section)

**Golden rule: the client never mutates subscription state.** Only Stripe's signed webhook does.

```text
User clicks "Upgrade" → POST /payments/create-checkout (server)
  → server creates a Stripe Checkout Session (server-only secret key)
  → server returns { checkout_url }
  → frontend does window.location.href = checkout_url   (pure redirect, no key on client)
  → Stripe handles card entry on Stripe's own PCI-DSS page (we never touch card data)

Stripe charges → POST /payments/webhook (Stripe → our server)
  → server verifies Stripe-Signature header with the webhook secret
  → server sets: is_subscribed=true, subscription_tier, subscription_customer_id, subscription_end
  → server returns 200 to Stripe (else Stripe retries)

User returns → frontend polls GET /payments/status (read-only) → UI updates
```

**Non-negotiables**
1. **`STRIPE_SECRET_KEY` and the webhook secret live only in backend env.** The frontend gets *at most* the publishable key (and with the redirect-only flow, even that is unnecessary).
2. **Never set `is_subscribed` from a client callback** (e.g. a `?success=1` redirect). The only writer is the verified webhook.
3. **Verify the webhook signature** (`Stripe-Signature` + `construct_event`) before trusting the event. Reject anything else.
4. **Idempotency:** webhook handler must tolerate duplicate delivery (check `event.id` / use a processed-events store) so Stripe's retries don't double-apply.
5. **Handle the full event lifecycle:** `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted` (cancel → downgrade), `invoice.payment_failed` (grace period, then downgrade).
6. **Portal for cancel/refund:** `POST /payments/portal` → Stripe Customer Portal. The user manages billing on Stripe's domain; our webhook reacts.
7. **Downgrade behavior:** when a subscription lapses, keep the user's data (photos/streak) but gate features. Never delete data on downgrade — this preserves goodwill and makes re-upgrade frictionless.
8. **Free-tier enforcement is a backend concern** (§12) — currently missing and must be built.

### 5.6 Secrets & environment (zero secrets in the client bundle)
| Secret | Where it lives | Exposed to browser? |
|---|---|---|
| `SECRET_KEY` (JWT) | backend env only | ❌ never |
| `STRIPE_SECRET_KEY`, webhook secret | backend env only | ❌ never |
| `DEEPSEEK_API_KEY` | backend env only | ❌ never |
| `CLOUDINARY_API_SECRET` | backend env only | ❌ never |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, per-request `signature` | served by `/upload/signature` | ✅ cloud_name + api_key are public by design; the *secret* never leaves the server (only a time-boxed signed token is returned) |
| `NEXT_PUBLIC_*` | frontend env | ✅ only for non-sensitive config (e.g. API base URL) |

**Rules:** `.env` is gitignored (verify); `.env.example` contains placeholders only; never log tokens or secrets; `SECRET_KEY` default is **refused in production** (config already raises `RuntimeError`).

### 5.7 XSS / CSP / CSRF / injection
- **XSS is the #1 realistic risk** because V1 stores the JWT in `localStorage`. Defenses:
  - **Strict CSP**: `default-src 'self'`; no `unsafe-inline` scripts; no `unsafe-eval`; images from `self` + Cloudinary; connect-src `self` + `https://lookmaxx-api.onrender.com` + Cloudinary.
  - **Zero third-party JS** in V1 (no ad scripts, no analytics iframes that run inline).
  - **React escapes by default.** Never use `dangerouslySetInnerHTML` with user/AI-generated text (full_name, bio, notes, AI plan text, product descriptions). AI text is rendered as plain text/React nodes only.
  - **Sanitize + length-cap** any user input on the client (Zod `max()` mirrors DB column limits) and re-validate on the server (Pydantic).
- **CSRF:** not applicable in V1 (no ambient cookies — the token is an explicit header). In Phase 2 (httpOnly cookie), add `SameSite=Lax` + CSRF token on the proxy.
- **Injection:** the backend uses SQLAlchemy ORM (parameterized) — no raw SQL with user input. Pydantic validates all request bodies.

### 5.8 CORS & API exposure
- Today: `allow_origins=["*"]`. **Lock to the Vercel domain before real traffic** (and keep `allow_credentials` false in V1 since we use bearer headers, not cookies).
- Public endpoints (no auth) are limited to: `/health`, `/auth/signup`, `/auth/login`. Everything else requires a valid JWT.

### 5.9 Rate limiting & abuse prevention
- **Existing:** Redis-backed sliding window, 60 req/min anonymous, 200 req/min authenticated; degrades to an in-memory limiter if Redis is down (so the API keeps working). `429` body: `{"detail":"Rate limit exceeded. Please wait a moment."}`.
- **To add (hardening):** per-route limits on `/auth/login` (e.g. 10/min/IP to stop credential stuffing) and on upload/analyze (e.g. 10/min per user) — the free tier also naturally caps analyses (§12).
- **Client behavior on `429`:** show a non-blocking toast, auto-retry with exponential backoff (cap ~3 retries), never hammer the endpoint.

### 5.10 Upload & file security
- **Extension allowlist:** `.jpg`, `.jpeg`, `.png`, `.heic` (400 otherwise).
- **Size cap:** 10 MB, enforced by streaming read (413 if exceeded).
- **Content validation:** `can_decode_image()` rejects non-image bytes (e.g. an HTML file renamed `.jpg`) with a clean 400 **before** they reach Cloudinary.
- **Cloudinary ownership check:** `/upload/save` rejects a `file_url` that doesn't contain our `CLOUDINARY_CLOUD_NAME`. *Harden later:* require the URL to match our signed `public_id`/`folder` (currently only a substring check).
- **Path/name safety:** server generates `public_id` (`user_{userid}_{random}`) — never trusts a client filename for storage.
- **Direct upload:** Cloudinary request is **signed per-request** and time-boxed; the API secret is never sent to the client.

### 5.11 Privacy (faces are biometric data)
- Photos are **private by default**: every photo route requires the owner's JWT and scopes by `user_id`.
- **Explore anonymization:** transformations expose only a first name (or "Member XXXX") + score deltas. ⚠️ **Open finding:** the current `/explore` response also returns raw `before_image_url` / `after_image_url`. For privacy, **do not render these** until we either (a) require explicit opt-in to be featured, or (b) server-blurs the faces. Treat as a P1 privacy fix before public launch.
- **GDPR deletion:** `DELETE /profile/delete` cascades to photos/plans/check-ins. The frontend offers this in Settings with a two-step confirm (typed phrase), and also requests Cloudinary deletion of the user's images.
- **No social login requirement** in V1 (email/password only) — reduces third-party data sharing.
- **Full GDPR & privacy compliance plan → §20** (legal basis, data inventory, consent capture, sub-processor DPAs, DPIA, retention, data-subject rights).

### 5.12 Security checklist (ship gate)
- [ ] `require_pro` dependency exists and is applied to all Pro-gated routes.
- [ ] `subscription_tier` is read from DB on every request (never from client).
- [ ] Stripe webhook verifies signature + is idempotent.
- [ ] No secret appears in the client bundle (`SECRET_KEY`, `STRIPE_SECRET_KEY`, `DEEPSEEK_API_KEY`, `CLOUDINARY_API_SECRET`).
- [ ] CORS locked to the Vercel domain.
- [ ] Strict CSP deployed; zero third-party inline scripts.
- [ ] `.env` gitignored; `.env.example` placeholders only.
- [ ] Explore stops returning raw face URLs (or blur + opt-in).
- [ ] `SECRET_KEY` not the default in production (config already enforces).
- [ ] Login rate-limited per IP.
- [ ] Every user input length-capped (client Zod + server Pydantic).

---

## 6. Design system (visual language)

> Token values live in `PSYCHOLOGY.md`. This section defines *how they are used*. The palette is **black + gold** (premium, high-status, "not a cheap scam app").

### 6.1 Color tokens & meaning
| Token | Use | Psychology |
|---|---|---|
| `background` (#0A0A0A / near-black) | App + landing background | Luxury, focus, seriousness |
| `surface` (#141414 / #1A1A1A) | Cards, panels | Depth without distraction |
| `gold` (#D4AF37 / #E5C158) | CTAs, score highlight, streak flame, Pro accents | Status, premium, achievement |
| `text-primary` (#F5F5F5) | Headlines, scores | Clarity |
| `text-muted` (#9CA3AF) | Secondary copy, labels | Hierarchy without noise |
| `success` (#22C55E) | Improving trend, check-in done | Reward |
| `warning` (#F59E0B) | Near milestone, "still working" | Anticipation, not alarm |
| `danger` (#EF4444) | Errors only (sparingly) | Only when something is actually wrong |
| `gold-gradient` | Hero score ring, paywall Pro card | Peak-End highlight |

**Rule:** `danger` is reserved for *errors*, never for low scores. A low score uses neutral text + improvement framing ("room to grow", never red).

### 6.2 Typography
- **Display / headlines:** Space Grotesk (distinctive, modern, confident). Used for the hero, score numbers, section titles.
- **Body / UI:** Inter (or system-ui fallback). Readable at small sizes.
- **Numbers:** tabular-nums so the count-up score and charts don't jitter.
- **Scale (px):** 12 / 14 / 16 / 18 / 20 / 24 / 32 / 48 / 64. Hero headline up to 64 on desktop, 40 on mobile.

### 6.3 Spacing, radius, elevation
- **Spacing:** 4px grid (4/8/12/16/24/32/48/64).
- **Radius:** cards 16px, buttons 12px (fully-rounded pill for primary CTA), inputs 12px.
- **Elevation:** cards use a subtle 1px border + soft shadow, not heavy drop shadows (keeps the dark theme clean).

### 6.4 Motion (fast, purposeful, respectful of `prefers-reduced-motion`)
| Element | Motion | Duration/easing |
|---|---|---|
| Score reveal | Count-up number + ring fill | 1.2 s, ease-out |
| Category bars | Animate width in on mount | 0.5 s, stagger 60 ms |
| Screen transition | Fade + 8px slide | 200 ms, ease-out |
| Button press | Scale 1 → 0.98 | 80 ms |
| Streak flame | Pulse on check-in | 0.6 s loop (once) |
| Skeleton | Soft shimmer | 1.4 s loop |
| Toast | Slide-in from top | 250 ms |
| Milestone | Confetti/burst + scale | 0.8 s |

**Rule:** every animation respects `prefers-reduced-motion: reduce` (fall back to instant/opacity-only). No infinite distracting loops except the analysis progress ring (which must be calm).

### 6.5 Component inventory (to scaffold)
**Primitives:** `Button` (variants: primary/gold, secondary/outline, ghost, danger; states: default/hover/active/disabled/loading), `Input`, `Card`, `Badge`, `ProgressRing`, `ScoreMeter`, `Skeleton`, `Dialog`, `Toast` (sonner), `Spinner`, `OfflineBanner`, `EmptyState`.
**Domain:** `Score` (tabular count-up), `CategoryBar`, `StreakFlame`, `BeforeAfterSlider`, `MilestoneTimeline`, `TransformCard` (anonymized), `TaskCheckbox`, `TierCard`, `LockChip`.
**Layout:** `AppShell` (top nav desktop + bottom tab nav mobile).

### 6.6 Dark theme only (V1)
Ship dark-first (it's the brand). Light theme is a Phase-2 nicety, not a blocker.

---

## 7. Information architecture & global shell

### 7.1 Route map
| Route | Auth | Purpose |
|---|---|---|
| `/` | ❌ | Landing (marketing + one CTA) |
| `/signup` | ❌ | Create account |
| `/login` | ❌ | Log in |
| `/onboarding` | ✅ | 3 micro-steps, skippable |
| `/upload` | ✅ | Capture/pick photo |
| `/analyzing/[photo_id]` | ✅ | Poll analysis progress |
| `/results/[photo_id]` | ✅ | Score + plan reveal |
| `/app` (or `/dashboard`) | ✅ | Home: score, streak, next action |
| `/plan` | ✅ | 90-day plan + daily tasks |
| `/progress` | ✅ | Chart + before/after + milestones |
| `/explore` | ✅ | Anonymized transformations + articles |
| `/products` | ✅ | Affiliate recommendations |
| `/upgrade` | ✅ | Paywall (3 tiers) |
| `/settings` | ✅ | Profile, billing, delete account |

### 7.2 Navigation (AppShell)
- **Desktop:** top nav — logo → Dashboard · Plan · Progress · Explore · Products · (Pro badge) · avatar menu (Settings · Sign out).
- **Mobile:** bottom tab bar — Dashboard · Plan · Progress · Explore · Settings (5 tabs). The active tab is gold; inactive is muted.
- **Pro status chip:** if `subscription_tier === "free"`, a subtle "Upgrade" chip appears in the nav (social-proof + status pressure, not nagging).
- **Offline banner:** a persistent thin banner appears when `navigator.onLine === false`, copy: *"You're offline — we'll sync when you're back."* It auto-hides on reconnect.

### 7.3 Global guards & boundaries (never-crash infrastructure)
1. **Route guard (`useRequireAuth`):** if no token, redirect to `/login?next=<path>` (validated allowlist). If token exists but `GET /auth/me` returns 401, clear token + redirect.
2. **Global Error Boundary (React):** wraps the whole app tree. If a render throws, it shows a friendly card — *"Something went wrong. Reload to continue."* + a Reload button — **never a blank white screen**.
3. **API client wrapper:** a single typed `apiFetch()` that (a) attaches the bearer token, (b) parses JSON defensively, (c) normalizes FastAPI `{detail}` errors into typed `ApiError {status, message, code}`, (d) maps network/timeout to a distinct error, (e) triggers the global 401 handler, (f) truncates/logs without secrets.
4. **Defensive schema decoding:** all server data is parsed through **Zod schemas with safe fallbacks** (e.g. `z.number().catch(0)`, `z.string().catch("")`, `z.array(...).catch([])`). A malformed field degrades to a safe default, never a throw.
5. **404 page:** friendly, branded, with a "Back to dashboard" CTA.

### 7.4 Auth boot sequence (on app load)
1. Read token from localStorage.
2. If absent → render public route (or redirect if inside `/app`).
3. If present → optimistically render, then `GET /auth/me`. On 401 → clear + redirect. On success → hydrate user + tier.
4. TanStack Query keys: `['me']`, `['dashboard']`, `['plan']`, `['analysis', id]`, `['progress']`, `['explore']`, `['products', tier]`, `['payments']`.
5. `staleTime`: dashboard/plan 30s, analysis 60s, explore/products 5min — fewer backend hits = lower cost.

---

## 8. Screen-by-screen specification

> Every screen uses the same template: **Purpose · Layout · Buttons · Inputs · States · Errors · Copy · Animation · API.** Each button lists its enabled/disabled/loading behavior. Each error lists the recovery action. This is the implementation contract.

### 8.1 Landing (`/`) — public
- **Purpose:** answer *"What's my score?"* in 3 s, drive one CTA. SEO is the growth channel → the page must render meaningful content without JS.
- **Layout:** black hero → huge headline "What's your score?" → gold CTA → blurred/looped "score reveal" teaser → 3 trust chips (Free · Private · 90-day plan) → anonymized transformations strip → footer (privacy, terms, contact).
- **Buttons:**
  - **"See your score — free"** (primary): scrolls to CTA or goes to `/signup`. Always enabled.
  - **"Log in"** (ghost, top-right): → `/login`. Enabled.
- **Inputs:** none.
- **States:** mobile hero (stacked); `prefers-reduced-motion` → static teaser (no loop); no-JS → real `<h1>`/`<p>` content (SSR).
- **Errors:** none (no API). If the optional public `/explore` preload fails → silently hide the strip, never an error.
- **Copy:** headline "What's your score?" · subhead "Upload one photo. Get your baseline score and a 90-day plan to improve it." · chips "Free · Private · 90-day plan".
- **Animation:** hero headline fade-up 400 ms; teaser is a slow loop (disabled for reduced-motion).
- **API:** none required.

### 8.2 Signup (`/signup`) — public
- **Purpose:** minimal friction — 3 fields max.
- **Layout:** centered card on black: email, password, (optional) first name, gold "Create account", micro-commitment subtext, link to `/login`.
- **Buttons:**
  - **"Create account"** (primary): disabled while loading or if Zod invalid; shows a spinner + "Creating…" during submit. On success → `/onboarding`.
  - **"Log in instead"** (link): → `/login`.
  - **Password visibility toggle** (eye): toggles `type` text/password.
- **Inputs (Zod → then Pydantic, both must agree):**
  - `email`: required, valid email, trim + lowercase, `maxLength 254`. `autocomplete="email"`, `type="email"`, `inputMode="email"`.
  - `password`: required, min 6, **never blocked paste**, `autocomplete="new-password"`.
  - `full_name`: optional, `maxLength 255`, trim.
- **States:** idle · submitting (spinner, inputs disabled) · success (redirect) · field-invalid (inline under field) · server-error (inline + toast).
- **Errors (see §9 for the full 20-scenario matrix):** duplicate email → *"That email is already registered. Log in instead."* + login link · invalid email → *"Enter a valid email address."* · short password → *"Password must be at least 6 characters."* · network → *"Can't reach the server. Check your connection and try again."* · 429 → *"Too many attempts. Wait a minute and try again."* · 500 → generic friendly message (never raw `detail`).
- **Copy:** subtext "Your score is private. Takes 60 seconds."
- **Animation:** card fade-up; field error shake (subtle, 200 ms).
- **API:** `POST /auth/signup` (JSON `email`, `password`, `full_name`). On success, also call `POST /auth/login` to auto-login; if auto-login fails → `/login` with email prefilled + toast "Account created — log in to continue."

### 8.3 Login (`/login`) — public
- **Purpose:** return a returning user to their score/plan.
- **Layout:** centered card: email, password, gold "Log in", link to `/signup`, "Forgot password?" (Phase 2 — no reset route yet; hide or mark "coming soon", never a dead link).
- **Buttons:**
  - **"Log in"** (primary): same loading/disabled behavior as signup.
  - **"Create account"** (link): → `/signup`.
  - **Password visibility toggle.**
- **Inputs:** `email` (same validation), `password` (required; no min-length on login — just required), `autocomplete="current-password"`, `enterKeyHint="go"`.
- **States:** idle · submitting · invalid · server-error · **rate-limited**.
- **Errors:** wrong email OR wrong password → identical *"Incorrect email or password."* (anti-enumeration) · empty fields → inline required · network/429/500 → same friendly mapping as signup.
- **Copy:** "Welcome back. Your score is waiting."
- **Animation:** card fade-up; error shake.
- **API:** `POST /auth/login` (OAuth2 form-urlencoded: `username`=email, `password`). Store JWT per §5.4; redirect to `?next` (allowlisted) or `/dashboard`.

### 8.4 Onboarding (`/onboarding`) — 3 micro-steps, skippable
- **Purpose:** collect just enough to personalize (age/gender drive gender-specific scoring; one goal drives the plan). **Never trap the user.**
- **Layout:** progress dots (1/3 · 2/3 · 3/3) → one question per step → Next / Skip.
  - Step 1: Age (numeric) + gender (Male / Female / Other).
  - Step 2: pick **one** primary goal from `improve_skin`, `jawline`, `confidence`, `symmetry`, `general`.
  - Step 3: "How serious are you?" (commitment lever) — Casual / Consistent / Locked in.
- **Buttons:**
  - **"Next"** (primary): disabled until the current step has a valid value; on last step becomes "Finish".
  - **"Skip"** (ghost, every step): advances without saving that step.
  - **"Back"** (ghost, steps 2–3).
- **Inputs:** age (2–3 digit, clamp 13–99; if < 13, politely block with "LookMaxx is for 13+."), gender (segmented control), goal (single-select cards), commitment (segmented).
- **States:** each step is self-contained; skipping is always possible; values persist if they navigate back.
- **Errors:** invalid age → inline "Enter your age." · network on save → toast + retry; **skipping a save never blocks progress** (onboarding can be completed later).
- **Copy:** Step 1 "Tell us about you." · Step 2 "Pick one goal. We'll build your plan around it." · Step 3 "Consistency beats intensity." · Finish "You're locked in. Let's get your score."
- **Animation:** step slide 200 ms; goal cards scale on select.
- **API:** `PUT /profile` (age/gender/goals) then `POST /profile/onboarding`. If `PUT` fails → retry; if it keeps failing → still allow "Finish" (mark onboarding server-side only when possible) — never a hard block.

### 8.5 Upload (`/upload`)
- **Purpose:** get a usable front-facing selfie with least friction.
- **Layout:** large camera/capture area OR "Choose photo" → live guide ("Face the light, look straight") → 10 MB cap indicator → privacy note ("Your photo is private and deleted anytime").
- **Buttons:**
  - **"Take photo"** (primary, mobile): opens camera capture (if `getUserMedia` is permitted).
  - **"Choose photo"** (secondary): opens file picker (`accept="image/jpeg,image/png,image/heic"`).
  - **"Cancel"** (ghost): back to dashboard.
- **Inputs:** file (JPG/PNG/HEIC, ≤10 MB). Client compresses to ≤1200px JPEG ~75% **before** upload.
- **States:** idle · capturing · compressing (progress %) · uploading (progress bar) · saving · **face-guide overlay**.
- **Errors (each with recovery):** wrong type → *"Use a JPG, PNG, or HEIC file."* (re-pick) · too large → *"That photo is too big. Max 10MB."* (re-pick smaller) · no clear face → *"We couldn't find a clear face. Try better lighting, facing forward."* (retry) · Cloudinary failure → *"Image upload failed. Try again."* (retry) · network/offline → *"No connection. Check your signal."* (retry on reconnect) · timeout → *"Upload is taking too long. Try a smaller photo."* (retry).
- **Copy:** "Face the light. Look straight. We'll handle the rest." · privacy note builds trust (reduces drop-off on the most sensitive step).
- **Animation:** upload progress bar animates smoothly; subtle "scanning" shimmer while compressing.
- **API:** `GET /upload/signature` → direct Cloudinary `POST` → `POST /upload/save` → `POST /photos/analyze/{photo_id}` → navigate to `/analyzing/{photo_id}`.

### 8.6 Analyzing (`/analyzing/[photo_id]`)
- **Purpose:** turn a 5–9 s wait into an *experience* (never let the user feel stuck or bored).
- **Layout:** the uploaded photo (subtly animated "scan" sweep) + a **progress ring** + rotating status copy + a calm sub-line.
- **Buttons:** **"Cancel"** (ghost): stops polling and returns to `/dashboard` (analysis continues in the background; the result will be there when they return).
- **Inputs:** none.
- **States:** polling (`pending`/`processing`) · **completed** → auto-navigate to `/results/{id}` · **failed** → friendly retry card · **timeout (>60 s)** → "still working" card with Retry poll / Back.
- **Errors:** `failed` status → *"Analysis couldn't complete. Try a clearer photo."* (retry / re-upload) · timeout → *"Still working… give it a moment, or retry."* (retry poll) · network → keep the last state, show offline banner.
- **Copy (rotating, ~2.5 s each, reassurance psychology):** "Reading your features…" → "Measuring symmetry…" → "Analyzing skin & jawline…" → "Building your 90-day plan…" → "Almost there…". Always positive, never "processing…" alone.
- **Animation:** calm progress ring (not a frantic spinner); gentle scan sweep; copy cross-fade.
- **API:** poll `GET /photos/{photo_id}` every 1.5 s, cap 60 s. **Never** `setState` on an unmounted component (guard the interval).

### 8.7 Results (`/results/[photo_id]`) — the "wow" screen
- **Purpose:** deliver the score + potential in a way that feels like an achievement and drives the next action.
- **Layout:** score ring (count-up) → score label → "potential score" + improvement gap → per-category bars (symmetry, skin, jawline, eyes, nose, lips) → strengths/weaknesses → CTA "Get your 90-day plan".
- **Buttons:**
  - **"Get your 90-day plan"** (primary): → `/plan` (or unlocks plan). On free tier, if plan is gated → `/upgrade` with a gentle lock message.
  - **"View recommendations"** (secondary): → `/products`.
  - **"Back to dashboard"** (ghost).
- **Inputs:** none.
- **States:** loading (skeleton ring + bars) · loaded · **plan still enriching** (DeepSeek runs in the background — show a subtle "Personalizing your plan…" chip, never block the score).
- **Errors:** 404 → *"Photo not found."* (back to dashboard) · analysis missing → *"This photo hasn't been analyzed yet."* (retry) · network → retry card.
- **Copy:** score labels are neutral-encouraging: e.g. 30–59 "Solid foundation", 60–79 "Strong features", 80–95 "Elite symmetry" (see `score_labels`). Improvement framing: "You're at 71 — your potential is ~84." Never "You're average."
- **Animation:** score count-up 1.2 s; ring fills; category bars stagger in (60 ms apart); potential score reveals with a subtle gold shimmer.
- **API:** `GET /analysis/{photo_id}` for the score + `GET /analysis/{photo_id}/plan` (plan may be a background-enriched result; poll once if missing).

### 8.8 Dashboard (`/app`)
- **Purpose:** the daily anchor — one glance: score, streak, next action.
- **Layout:** greeting + current score card → streak flame + "Day X/90" → next-action card → milestone preview → quick links (Upload new photo · View plan · Products).
- **Buttons:**
  - **"Upload new photo"** (primary): → `/upload`. On free tier after the 1st analysis, tapping it can deep-link to `/upgrade` (with the backend `403` as the authoritative gate — the UI hint is just UX).
  - **"Log today's check-in"** (primary when pending): calls check-in → streak bump.
  - **"View plan" / "View progress" / "Shop products"** (secondary cards).
- **Inputs:** none.
- **States:** loading (skeleton cards) · **empty** (no photo yet) → *"Upload your first photo"* CTA · error (retry card) · offline banner.
- **Errors:** 401 → global redirect · network/500 → retry card *"Something went wrong. Please try again."* · empty plan → "Upload and analyze a photo to get your plan."
- **Copy:** greeting uses first name if present ("Welcome back, Alex."); next-action uses the backend `next_action` (already psychology-tuned).
- **Animation:** streak flame pulses when a check-in lands; cards stagger in.
- **API:** `GET /dashboard` (single call returns profile + plan + progress + milestones + next_action). Cache 30 s.

### 8.9 Plan (`/plan`)
- **Purpose:** the retention engine — daily 2-minute tasks, phase progress, streaks.
- **Layout:** "Day X/90" header → phase label (Phase 1/2/3) → today's tasks as checkboxes → week timeline → milestone chips.
- **Buttons:**
  - **Task checkboxes** (toggle): optimistic update → `POST /plan/checkin` (or `POST /progress/checkin`). On success → streak bump + toast; on failure → revert checkbox + toast.
  - **"Check in"** (primary): submits today's completed tasks.
  - **"Next milestone"** (read-only chip): no action.
- **Inputs:** checkboxes only.
- **States:** loading (skeleton task list) · **empty** ("No active plan — analyze a photo" CTA) · partially-completed (checked tasks persist) · error (retry).
- **Errors:** 403 (free tier gated) → `/upgrade` · network → revert + toast · no plan → upload CTA.
- **Copy:** "Day 12/90 — stay consistent to build lasting habits." · Zeigarnik: incomplete tasks are visually emphasized (unfinished = "pull back in").
- **Animation:** checkbox tick draws in; streak flame pulses; milestone celebration (confetti) on hitting Day 7/14/21/30/45/60/75/90.
- **API:** `GET /plan` + `POST /plan/checkin`. Milestones come from the same response (completed + next 3 upcoming).

### 8.10 Progress (`/progress`)
- **Purpose:** Peak-End — show them changing. The before/after slider is the single most persuasive asset in the app.
- **Layout:** score-over-time line chart → **before/after slider** (baseline vs latest) → milestone timeline → total check-ins/streak summary.
- **Buttons:**
  - **Before/after slider handle** (drag): reveals baseline vs latest photo.
  - **"Upload progress photo"** (secondary): → `/upload` (check-in photo path).
  - **"Share"** (Phase 2 only): not in V1.
- **Inputs:** slider only.
- **States:** loading (chart skeleton) · **fewer than 2 photos** → *"Take your next progress photo at Day 30."* (don't render a broken comparison) · error (retry) · offline.
- **Errors:** no photos → empty state · network/500 → retry · 404 (photo missing) → skip that datapoint, render the rest.
- **Copy:** if trend is "improving": "You're up +9.6 pts since Day 1. That's real." · if "stable": "Holding steady — the next photo will show the work." · if "declining" (rare): neutral "Progress isn't linear. Keep the streak alive." (never shame).
- **Animation:** chart line draws in; slider glides; milestone dots pulse when reached.
- **API:** `GET /analysis/progress/all` (timeline) + `GET /progress/photos/compare` (baseline vs latest) + `GET /progress/milestones`.

### 8.11 Explore (`/explore`)
- **Purpose:** social proof + education. Keeps engaged users engaged without requiring a photo.
- **Layout:** anonymized transformation cards ("Alex: 71 → 84") → article cards (evergreen content).
- **Buttons:**
  - **Transformation card** (tap): opens a detail view (score deltas only — **no raw face URLs rendered** per §5.11 until privacy fix).
  - **Article card** (tap): opens the article link in a new tab (`rel="noopener noreferrer"`).
- **Inputs:** none.
- **States:** loading (card skeletons) · **empty transformations** → show articles only (never fake data) · error (retry) · offline.
- **Errors:** network/500 → retry card · empty → "Articles coming soon" only if both lists are empty.
- **Copy:** transformation caption "Alex: 71 → 84" (real deltas, anonymized). Trust line: "Real members. Real progress."
- **Animation:** cards stagger in; score delta counts up on hover/entering viewport.
- **API:** `GET /explore` → `{transformations, articles}`. Cache 5 min.

### 8.12 Products (`/products`)
- **Purpose:** secondary monetization (affiliate) *after* value is established.
- **Layout:** header "Because your weakest areas are skin & jawline…" → product grid → budget filter (Budget / Mid / Premium) → affiliate disclosure.
- **Buttons:**
  - **Budget filter tabs** (Budget/Mid/Premium): refetch `?tier=`; active tab is gold.
  - **Product card** (tap): opens affiliate link in new tab (`rel="noopener noreferrer sponsored"`).
- **Inputs:** none (filter only).
- **States:** loading (grid skeletons) · **empty** ("No recommendations yet — analyze first") · error (retry) · offline.
- **Errors:** 400 invalid tier → reset filter to Mid · network/500 → retry.
- **Copy:** transparent disclosure "We may earn a commission" (transparency = trust; the audience distrusts hidden affiliate links).
- **Animation:** grid stagger-in; card hover lift.
- **API:** `GET /products/recommendations?tier=budget|mid_range|premium&max_results=8` + `GET /products/categories`.

### 8.13 Paywall (`/upgrade`)
- **Purpose:** convert hooked users. 3 tiers, Pro highlighted, annual toggle anchoring. **Honesty rule:** until the backend `/payments/*` routes exist, show a "join waitlist" state — never a fake checkout.
- **Layout:** tier cards (Free / **Pro** / Elite) → Pro highlighted with gold border + "Most popular" badge → annual/monthly toggle with "save 58%" anchor → FAQ/risk-reversal row.
- **Buttons:**
  - **Annual/Monthly toggle** (segmented): flips prices; annual is preselected (anchor).
  - **"Start Pro" / "Go Elite"** (primary on Pro, secondary on Elite): if payments are live → `POST /payments/create-checkout` → redirect to Stripe. If not live → "Join waitlist" (collects email in a toast state, never fakes a charge).
  - **"Maybe later"** (ghost): closes the paywall, returns to where they came from (never traps).
  - **"Manage billing"** (if subscribed): → Stripe Customer Portal (`POST /payments/portal`).
- **Inputs:** none (waitlist email reuses the account email).
- **States:** loading (price fetch) · live-checkout · waitlist · **already Pro** (shows "You're on Pro — manage billing").
- **Errors:** checkout-create failure → *"Payment couldn't start. Try again."* (retry) · Stripe return with `?canceled` → toast "No charge was made." · webhook-not-yet-confirmed → poll `/payments/status` (read-only) with a calm "Confirming your upgrade…".
- **Copy (loss framing + risk reversal):** "Keep your streak & history synced. Cancel anytime." · "Don't lose your progress." · anchor "save 58% with annual."
- **Animation:** tier cards lift on hover; Pro card has a subtle gold pulse; price cross-fades on toggle.
- **API:** `POST /payments/create-checkout` (to build), `POST /payments/portal` (to build), `GET /payments/status` (read-only). **Gating is enforced server-side via `require_pro` (§5.3, §12).**

### 8.14 Settings / Profile (`/settings`)
- **Purpose:** account control — profile edit, billing, delete (GDPR), sign out. Minimal but complete.
- **Layout:** profile form (full_name, age, gender, goals, height, weight, location, bio) → subscription section (current tier, manage billing) → danger zone (delete account).
- **Buttons:**
  - **"Save changes"** (primary): `PUT /profile`; disabled while saving; validates client-side first.
  - **"Manage billing"** (secondary, if subscribed): Stripe portal.
  - **"Sign out"** (ghost): clears token, redirects `/`.
  - **"Delete account"** (danger): two-step confirm (type "DELETE") → `DELETE /profile/delete` → clear token → `/`.
- **Inputs:** full_name (≤255), age (13–99), gender (segmented), goals (multi-select), height/weight (numeric, cm/kg), location (≤255), bio (≤500, rendered as plain text only).
- **States:** loading (fetch profile) · saving · saved (toast "Profile updated.") · confirm-delete dialog · deleted (redirect).
- **Errors:** 400 no fields → "Change something first." · network/500 → retry · delete failure → "Couldn't delete your account. Try again."
- **Copy:** danger zone is explicit and calm: "This permanently deletes your photos, plan, and progress. This can't be undone."
- **Animation:** save button spinner; delete confirm dialog scales in.
- **API:** `GET /profile`, `PUT /profile`, `DELETE /profile/delete`. (Billing via `/payments/*` when built.)

---

## 9. Error & message handling (never-crash rules + full catalog)

### 9.1 The never-crash contract (rules every screen obeys)
1. **Errors are inline + toast, never a blank red screen.** Field errors appear *under the field*; general errors appear as a non-blocking toast and/or a retry card.
2. **Every error has a recovery action** — retry / back / fix the input. No dead ends.
3. **`401` always clears the session and redirects** to `/login` (global handler). The user is never left staring at a broken authenticated screen.
4. **Loading, empty, and error states are designed** (skeletons match layout; empty states include the next action).
5. **Never render raw backend `detail` verbatim as the primary message** — it may contain technical text. Map it to friendly copy (table below). Log the raw detail to the console (truncated), never to the user.
6. **Defensive parsing:** every API response is decoded through a Zod schema with `.catch()` fallbacks, so a missing/`null`/wrong-typed field degrades to a safe default (0, "", []) instead of throwing.
7. **Network vs server vs auth errors are distinguished** so the message and recovery are correct (offline → "check your signal"; 500 → "try again"; 401 → redirect).
8. **Timeouts:** fetch uses an AbortController (e.g. 20 s upload, 10 s JSON); a timeout is a first-class error with its own copy, not a hang.
9. **Unmounted-state guard:** polls and async setters are canceled/guarded on unmount — no "setState on unmounted" leaks.
10. **DeepSeek/plan fallback is invisible:** if the AI plan isn't ready, serve the template plan and *never* tell the user it's "fake" — deliver value silently.

### 9.2 Signup & login — full 20-scenario matrix (build & test every one)

| # | Scenario | Expected | User-facing copy / action |
|---|---|---|---|
| 1 | Valid signup (email+password+name) | 201 → `/onboarding` | Toast "Account created." |
| 2 | Duplicate email | 400 `Email already registered` | *"That email is already registered. Log in instead."* + login link |
| 3 | Email with leading/trailing spaces | backend trims → succeeds | Client also trims before send |
| 4 | Email mixed case `Foo@Bar.com` | backend lowercases | No duplicate account created |
| 5 | Invalid email (no @/TLD) | Zod blocks; 422 if it reaches backend | *"Enter a valid email address."* |
| 6 | Password < 6 chars | Zod blocks; 422 otherwise | *"Password must be at least 6 characters."* |
| 7 | Empty email or password | Zod blocks on blur/submit | *"Email is required."* / *"Password is required."* |
| 8 | Password of only spaces | `.strip()` → empty → reject | *"Password can't be empty."* |
| 9 | Email > 254 chars | client `maxLength=254` | Prevent DB `VARCHAR(255)` overflow |
| 10 | Existing email, different case | same as #4 — no duplicate | Backend lowercases both signup & login |
| 11 | Network down / DNS fail | no response → timeout | *"Can't reach the server. Check your connection and try again."* |
| 12 | Rate limited | 429 | *"Too many attempts. Wait a minute and try again."* |
| 13 | Server 500 | global handler → friendly 500 | *"Something went wrong on our end. Please try again."* (never raw detail) |
| 14 | Signup ok but auto-login fails | fallback | → `/login` prefilled + toast "Account created — log in to continue." |
| 15 | Password manager autofill/paste | must work — **never block paste** | `autocomplete="new-password"/"current-password"` |
| 16 | Mobile keyboard | correct type/inputMode | `type="email"`, `inputMode="email"`, `enterKeyHint="go"` |
| 17 | Internationalized email (Unicode local part) | backend `EmailStr` accepts | Client must not over-reject |
| 18 | Login wrong password | 401 | *"Incorrect email or password."* (same as wrong email — anti-enumeration) |
| 19 | Login nonexistent email | 401 | *"Incorrect email or password."* |
| 20 | Login then token expires (30 min) | 401 on next call | Global 401 handler clears token → `/login` |

### 9.3 Upload & analysis — full error catalog

| Scenario | Status | User-facing copy | Recovery |
|---|---|---|---|
| File too large | 413 | *"That photo is too big. Max 10MB."* | Re-pick smaller |
| Unsupported file type | 400 | *"Use a JPG, PNG, or HEIC file."* | Re-pick |
| Corrupt / non-image bytes | 400 | *"We couldn't read that image. Try a different photo."* | Re-pick |
| Validation failed (no clear face) | 400 | *"We couldn't find a clear face. Try better lighting, facing forward."* | Retry upload |
| Rate limit | 429 | *"Too many requests. Wait a moment."* | Auto-retry after backoff |
| Server error | 500 | *"Something went wrong. Please try again."* | Retry |
| Network / offline | — | *"No connection. Check your signal."* | Retry on reconnect |
| Upload timeout | — | *"Upload is taking too long. Try a smaller photo."* | Retry |
| Cloudinary failure | 500 | *"Image upload failed. Try again."* | Retry |
| Analysis `failed` status | — | *"Analysis couldn't complete. Try a clearer photo."* | Retry / re-upload |
| Analysis timeout (>60s poll) | — | *"Still working… give it a moment, or retry."* | Retry poll |
| DeepSeek fallback (not an error) | — | *(silent)* — serve template plan | Never say it's "fake" |

### 9.4 HTTP status → copy map (used by the API client)

| Status | Meaning | Copy | Action |
|---|---|---|---|
| 400 | Bad input | Map by endpoint (see above) | Fix input |
| 401 | Unauthenticated | *(silent redirect)* | Clear token → `/login` |
| 403 | Not allowed (e.g. free tier) | *"Upgrade to Pro to unlock this."* | → `/upgrade` |
| 404 | Not found | *"Not found."* (+ context: photo/plan) | Back / retry |
| 413 | Too large | *"That photo is too big. Max 10MB."* | Re-pick |
| 422 | Validation | Map Pydantic field → inline error | Fix input |
| 429 | Rate limited | *"Too many requests. Wait a moment."* | Backoff retry |
| 500 | Server error | *"Something went wrong on our end. Please try again."* | Retry |
| Timeout | No response | *"Can't reach the server. Check your connection and try again."* | Retry |
| Offline | No network | *"You're offline — we'll sync when you're back."* | Banner, auto-resume |

### 9.5 Safe-message handling (so bad responses can never crash us)
- **`detail` may be a string OR an array** (FastAPI 422 returns `detail: [{loc, msg, ...}]`). The client normalizes both into one readable message (array → join `msg` fields).
- **HTML/script in a message:** never rendered as HTML. React text nodes are inherently safe. No `dangerouslySetInnerHTML` for any server/AI/user string.
- **Very long messages:** truncate to ~200 chars for display.
- **Unknown/absent fields:** Zod `.catch()` fallbacks (score→0, arrays→[], strings→""). A photo with `score: null` renders "—" not a crash.
- **Non-JSON response** (e.g. a proxy/HTML error page): the client catches the parse error and treats it as a 500.
- **`success`-wrapped responses:** some endpoints return `{success, message, data}`; the client checks `success` where present and surfaces `message` as a toast, never a screen.
- **Defensive image rendering:** `file_url` must be a valid http(s) URL (and, per §5.11, we don't render raw Explore face URLs). A broken image URL falls back to a placeholder, not a layout break.

---

## 10. Loading, empty & error-state emotional design (never feel bad while waiting)

| Screen | Loading | Empty | Error |
|---|---|---|---|
| Landing | SSR content (no spinner) | n/a | (no API) |
| Dashboard | Skeleton cards (match layout) | *"Upload your first photo"* CTA | Retry card |
| Plan | Skeleton task list | *"No active plan — analyze a photo"* CTA | Retry |
| Progress | Chart skeleton | *"No photos yet"* + next step | Retry |
| Explore | Card skeletons | *"Articles coming soon"* (never fake) | Retry |
| Products | Grid skeletons | *"No recommendations yet — analyze first"* | Retry |
| Analysis | Progress ring + rotating copy | — | Friendly retry |
| Results | Skeleton ring + bars | — | Retry / back |
| Upload | Progress bar + guide | — | Re-pick / retry |

**Emotional rules for waiting:**
1. **Never a bare spinner on a blank page.** Every loading state has context (skeleton = "content is coming", progress ring + copy = "work is happening").
2. **Rotating reassurance copy** during analysis turns an 8-second wait into a story ("Reading your features… → Building your 90-day plan…"). The wait feels purposeful.
3. **Skeletons match the final layout** — zero layout shift, so nothing "jumps" when data arrives (reduces perceived slowness).
4. **Loading never blocks navigation.** The user can leave `/analyzing` (background analysis continues) and the result is waiting when they return.
5. **Progress over precision:** show "Day 12/90", "7-day streak", "you're up +9 pts" — concrete, personal, motivating — not generic "loading…".
6. **Empty states always contain the next action** (never a dead "nothing here").

## 11. Engagement & psychology engine (the retention machine)

| Mechanism | Implementation | Where |
|---|---|---|
| **Zeigarnik effect** | Incomplete daily tasks are visually emphasized (unfinished = pull back in) | Plan |
| **Loss aversion** | Consecutive-day streak; "don't lose your streak" paywall copy | Dashboard, Plan, Upgrade |
| **Progress principle** | Milestone celebrations at Day 7/14/21/30/45/60/75/90 | Plan, Progress |
| **Peak-End rule** | Before/after slider at Day 30/60/90; big score reveal | Progress, Results |
| **Commitment & consistency** | Onboarding "How serious are you?" + skippable steps | Onboarding |
| **Social proof** | Anonymized transformations ("Alex: 71 → 84") | Explore |
| **Status / scarcity** | "top 20% of users", "Pro" badge, "Most popular" tier | Dashboard, Upgrade |
| **Anchoring** | Annual toggle "save 58%"; Pro vs Elite decoy pricing | Upgrade |
| **Risk reversal** | "Cancel anytime", "no card required", "private" | Landing, Upgrade |
| **Variable reward** | Score reveal is the surprise; potential score adds a "what's possible" hook | Results |

**Daily loop:** open → see streak + next action → complete 2-minute task → streak bump + dopamine toast → "come back tomorrow to keep the streak." The streak is the habit hook; the milestone is the long-horizon goal; the before/after is the payoff.

**Emotional trigger vocabulary (§3.4) is applied consistently** — every toast, empty state, and error uses the "words that work" column, never the "words that don't."

---

## 12. Monetization & premium gating

### 12.1 Tiers (pricing + anchoring)
| Tier | Price | Includes | Psychology role |
|---|---|---|---|
| **Free** | $0 | 1 analysis, streak tracking, baseline score | Hook — prove value |
| **Pro** | $9.99/mo (annual = anchor "save 58%") | Unlimited analyses, full 90-day plan, check-ins, recommendations | The target |
| **Elite** | $19.99/mo | Pro + 1:1 "coach" Q&A + priority | Decoy — makes Pro look like the smart buy |

### 12.2 What is gated (server-authoritative — see §5.3)
| Capability | Free | Pro/Elite | Enforced by |
|---|---|---|---|
| 1st analysis | ✅ | ✅ | backend (count analyses) |
| 2nd+ analysis | ❌ | ✅ | **`require_pro` on `POST /photos/analyze/{id}`** |
| Full 90-day plan | ❌ (teaser only) | ✅ | `require_pro` on `GET /analysis/{id}/plan` |
| Daily check-ins | ❌ | ✅ | `require_pro` on `POST /plan/checkin` |
| Product recommendations | ✅ (limited) | ✅ (full) | optional tier filter |

### 12.3 The missing piece (must build — this is the real monetization work)
The `User` model already has `is_subscribed`, `subscription_tier`, `subscription_start/end`, `subscription_customer_id`. What's missing:
1. **`require_pro` dependency** (FastAPI) — checks `current_user.is_subscribed` + tier from the DB; raises `403 "Upgrade to Pro to unlock this feature"`. **Apply it to the routes above.**
2. **`POST /payments/create-checkout`** — creates a Stripe Checkout Session, returns `{checkout_url}`.
3. **`POST /payments/portal`** — returns the Stripe Customer Portal URL (manage/cancel).
4. **`POST /payments/webhook`** — verifies `Stripe-Signature`, updates subscription fields (§5.5).
5. **`GET /payments/status`** — read-only tier + expiry (or reuse `GET /profile`).

**Free-tier analysis counting:** add a helper that counts the user's analyzed photos and rejects the 2nd+ without an active subscription. This is the *only* thing that actually monetizes the app — the paywall UI is just a doorway to it.

### 12.4 Paywall honesty (frontend contract)
- Until the backend routes exist, `/upgrade` shows **"Join waitlist"** — never a fake checkout that pretends to charge.
- The frontend **hides Pro UI as UX polish only**; it does not rely on it. If a user "unhides" a button in DevTools, the backend still returns 403.
- On a 403 from a gated action, the client deep-links to `/upgrade` with a friendly lock message — never a hard error.

### 12.5 Affiliate products (secondary revenue)
- Recommendations are **transparent**: "We may earn a commission" (the audience distrusts hidden affiliate links — honesty converts better here).
- All affiliate links open in a new tab with `rel="noopener noreferrer sponsored"`.

---

## 13. Data model & API contract

### 13.1 Core entities (mirrors `backend/app/models.py`)
- **User:** `id`, `email` (unique), `hashed_password`, `full_name`, `age`, `gender`, `goals[]`, `height`, `weight`, `location`, `bio`, `onboarding_completed`, `is_subscribed`, `subscription_tier` (free/pro/elite), `subscription_start/end`, `subscription_customer_id`, `plan_start_date`, `current_day`, `target_score`, `total_checkins`, `current_streak`, `longest_streak`, `last_checkin_date`, timestamps.
- **Photo:** `id`, `user_id`, `file_url`, `file_size`, `file_type`, `score`, `symmetry/skin/jawline/eye/nose_score`, `face_shape`, `analysis_details{}`, `strengths[]`, `weaknesses[]`, `analysis_status` (pending/processing/completed/failed), `is_baseline`, `week_number`, `captured_at`.
- **Plan:** `id`, `user_id`, `photo_id`, `total_days` (90), `current_day`, `current_phase`, `current_week`, `data{}`, `phases{}`, `daily_tasks[]`, `milestones[]`, `recommended_products[]`, `is_active`, timestamps.
- **UserCheckin:** `id`, `user_id`, `week_number`, `photo_id`, `progress_score`, `notes`, `completed_tasks[]`, `created_at`.

### 13.2 API contract (frontend ↔ backend, base `/api/v1`)
| Frontend action | Call(s) |
|---|---|
| Signup | `POST /auth/signup` → auto `POST /auth/login` |
| Login | `POST /auth/login` (OAuth2 form) → store JWT |
| Load me | `GET /auth/me` |
| Onboarding | `PUT /profile` + `POST /profile/onboarding` |
| Upload | `GET /upload/signature` → Cloudinary → `POST /upload/save` → `POST /photos/analyze/{id}` |
| Poll analysis | `GET /photos/{id}` (1.5 s, 60 s cap) |
| Show result | `GET /analysis/{photo_id}` + `GET /analysis/{photo_id}/plan` |
| Dashboard | `GET /dashboard` |
| Plan/tasks | `GET /plan` + `POST /plan/checkin` |
| Progress | `GET /analysis/progress/all` + `GET /progress/photos/compare` + `GET /progress/milestones` |
| Explore | `GET /explore` |
| Products | `GET /products/recommendations?tier=` + `GET /products/categories` |
| Upgrade | `POST /payments/create-checkout` (to build), `GET /payments/status` |
| Settings | `GET/PUT /profile`, `DELETE /profile/delete` |

**Response-shape safety:** frontend Zod schemas mirror backend Pydantic models; every field decodes with a `.catch()` fallback (§9.5). TypeScript types are generated from these Zod schemas so the compiler catches drift.

---

## 14. Performance, scalability & cost

### 14.1 Frontend budgets (founder lens)
- **LCP < 2.5 s on 4G.** Landing page < 150 KB JS gzipped (code-split the app behind `/app`; the marketing page ships almost no JS).
- **Images:** Cloudinary `f_auto,q_auto` + `next/image` (responsive `srcset`). Never ship a >200 KB hero. Photos are auto-converted to WebP.
- **Fonts:** `next/font` self-hosted + subset → no render-blocking Google Fonts, no layout shift.
- **JS:** route-level code splitting (Next.js dynamic imports); heavy libs (chart, compression) are lazy-loaded on their screens only.

### 14.2 Backend (already optimized — respect these constraints)
- **Render starter 512 MB, 1 worker.** Never add boot-time heavy imports — PyTorch/MediaPipe stay lazy-loaded.
- **Background analysis** keeps the upload response fast (~1.5 s) instead of blocking ~8.8 s.
- **Direct Cloudinary upload** keeps image bytes off the small worker (cheap + fast).
- **Plan caching:** `GET /plan` reuses the plan tied to the latest analyzed photo — repeat calls are instant.
- **Rate limiter** is Redis-backed with in-memory fallback (shared across workers when Redis is up).

### 14.3 Scaling path (when traffic grows)
1. Vercel auto-scales the frontend (static + serverless).
2. Move from Render starter → more RAM (ML is memory-hungry) and >1 worker; Redis becomes mandatory for the shared rate limiter.
3. Add the Next.js `/api/*` proxy → httpOnly cookie auth + hiding backend origin + edge caching of public content.
4. Optional: cache `/explore` and product lists at the edge (5 min) to cut backend load.
5. Move ML inference to a dedicated worker/queue (e.g. Celery + Redis) so a slow analysis never blocks API responses.

> Full production-ops playbook (caching layers, load balancing, observability, backups, CI/CD) → **§21**.

## 15. Accessibility

- **Color contrast:** gold on black and muted text meet WCAG AA (≥4.5:1 for body text). Color is never the only signal (icons + labels always accompany).
- **Keyboard:** every control is focusable and operable (buttons, checkboxes, sliders, tabs). Visible focus ring (gold outline).
- **Screen reader:** semantic HTML (`<button>`, `<label>`, `aria-live` for toasts and the analysis status), alt text on images, `aria-valuenow` on progress rings/sliders.
- **Reduced motion:** all animations respect `prefers-reduced-motion: reduce` (§6.4).
- **Touch targets:** ≥44×44 px on mobile (bottom nav, checkboxes, toggles).
- **Forms:** every input has a visible `<label>` and inline error text wired via `aria-describedby`.

---

## 16. Testing matrix (every scenario, before ship)

| Area | Scenarios | Tool |
|---|---|---|
| **Auth** | the full 20-scenario matrix (§9.2) | Playwright (E2E) + Vitest (unit) |
| **Upload** | every error in §9.3 (type, size, corrupt, no-face, Cloudinary fail, timeout, offline) | Playwright + MSW (mock) |
| **Analysis** | pending→processing→completed; `failed`; >60 s timeout; poll on unmount | Playwright + fake timers |
| **Premium gating** | free user hits 2nd analysis → 403 → `/upgrade`; DevTools-unhiding still blocked | integration test against a `require_pro`-stubbed API |
| **Payments** | create-checkout → redirect; webhook updates tier; cancel → downgrade; duplicate webhook (idempotency) | backend tests + mocked Stripe |
| **Streaks/milestones** | check-in bumps streak; Day 7/30/60/90 celebrations; missing a day resets streak | unit + Playwright |
| **Never-crash** | malformed JSON, `null` score, HTML in a field, non-JSON response, network drop | unit (Zod decoding) + E2E |
| **Responsive** | all screens at 375px / 768px / 1440px; touch targets | Playwright viewports |
| **Accessibility** | keyboard-only walkthrough, axe scan, reduced-motion | axe + manual |
| **Performance** | LCP < 2.5 s, landing JS < 150 KB | Lighthouse CI |

**Regression rule:** any new screen ships with its loading, empty, and error states *and* a test for each. A screen is "done" only when all three states are tested (§19).

## 17. Analytics & measurement (Phase 2, privacy-respecting)

- **Funnel (no PII):** landing visit → signup → onboarding complete → first upload → analysis complete → plan viewed → upgrade.
- **Activation:** % of signups that complete a first analysis within 24 h (the "aha" moment).
- **Retention:** D1/D7/D30 return rate; streak distribution; check-in frequency.
- **Monetization:** free→Pro conversion, churn, affiliate CTR, refund rate.
- **Engagement quality:** average session, before/after views, milestone completion.
- **Instrumentation rule:** use a self-hosted/privacy-first event (e.g. PostHog or a tiny internal counter) — never a third-party script that violates our CSP (§5.7). Events carry no faces, no emails, no tokens.

---

## 18. Run, deploy & GitHub readiness

### 18.1 Local development
```bash
# Backend (already working)
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in real values
uvicorn app.main:app --reload --port 8000
# Swagger: http://localhost:8000/docs

# Frontend (Next.js — to scaffold)
cd frontend
npm install
cp .env.example .env.local    # NEXT_PUBLIC_API_URL=https://lookmaxx-api.onrender.com/api/v1
npm run dev
# http://localhost:3000
```

### 18.2 Environment variables
| Var | Where | Notes |
|---|---|---|
| `SECRET_KEY` | backend | strong random; **required** in production (default is refused) |
| `DATABASE_URL` | backend | Postgres (Render) |
| `REDIS_URL` | backend | optional (in-memory fallback works for V1) |
| `DEEPSEEK_API_KEY` | backend | fallback plan if missing |
| `CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET` | backend | required for uploads |
| `STRIPE_SECRET_KEY`, webhook secret | backend | only when payments are built |
| `NEXT_PUBLIC_API_URL` | frontend | non-sensitive base URL |

**Rules:** `.env` is gitignored; `.env.example` ships placeholders only; no real secret is ever committed.

### 18.3 Deploy
- **Backend:** Render (see `backend/render.yaml`). Push to the Git remote → Render auto-deploys.
- **Frontend:** Vercel → import the repo → set `NEXT_PUBLIC_API_URL` → deploy. Custom domain optional.

### 18.4 Making the repo job-application-ready
The repo should read like a production project to a hiring manager. Requirements:
1. **`README.md`** — polished: badges (license, build, deploy), architecture diagram, feature list, security highlights, quick start, tech stack, screenshots placeholders, license.
2. **Clean git history** — small, well-named commits (`feat: add signup flow`, `fix: clamp category scores`).
3. **`PRODUCT_SPEC.md`** — this file proves you think in whole products, not just code.
4. **`.gitignore`** — excludes `node_modules`, `.env`, `venv`, `__pycache__`, the 94 MB ML model, build artifacts.
5. **`LICENSE`** — MIT (or chosen).
6. **Tests that run** — `cd backend && pytest`, `cd frontend && npm test` (once scaffolded).
7. **No secrets in history** — verify with `git log -p | grep -i secret` before making public.

## 19. Definition of done (a screen ships only when ALL are true)
- [ ] Purpose, layout, and copy match §8.
- [ ] Every button has default/hover/active/disabled/loading states.
- [ ] Every input validates client-side (Zod) and maps server errors to inline fields.
- [ ] Loading, empty, and error states are implemented (not afterthoughts).
- [ ] Every error shows a recovery action (retry/back/fix).
- [ ] `401` clears session + redirects; 403 deep-links to `/upgrade`.
- [ ] No raw backend `detail` is rendered verbatim; all responses decode defensively.
- [ ] Animations respect `prefers-reduced-motion`.
- [ ] A test exists for the happy path + each error + empty state.
- [ ] Premium-gated actions are enforced server-side (never UI-only).
- [ ] Privacy consent captured at signup; no raw face URLs exposed anywhere (§20).
- [ ] Gating/entitlement reads are always live (never cached); personalized responses are never publicly cached (§21.1).
- [ ] Logs redact faces, tokens, and emails (§21.3).

---

## Appendix A — API error reference (backend → client)

| Endpoint | Error | Status | Client mapping |
|---|---|---|---|
| `/auth/signup` | `Email already registered` | 400 | "That email is already registered…" + login link |
| `/auth/signup` | Pydantic `422` | 422 | inline field errors |
| `/auth/login` | `Incorrect email or password` | 401 | single generic message |
| `/auth/*`, all protected | `Could not validate credentials` | 401 | global 401 → `/login` |
| `/photos/upload`, `/progress/photos/upload` | unsupported format | 400 | "Use a JPG, PNG, or HEIC file." |
| `/photos/upload` | `File too large` | 413 | "That photo is too big. Max 10MB." |
| `/photos/upload` | `Could not read this image` | 400 | "We couldn't read that image…" |
| `/upload/save` | `Invalid file_url` | 400 | "Image upload failed. Try again." |
| `/photos/{id}`, `/analysis/{id}` | `Photo not found` | 404 | "Photo not found." + back |
| `/analysis/{id}` | `This photo has not been analyzed yet` | 404 | "This photo hasn't been analyzed yet." + retry |
| `/analysis/{id}/plan` | `No action plan found` | 404 | "Upload and analyze a photo to get your plan." |
| `/products/category/{cat}` | `Invalid category` / `Invalid tier` | 400 | reset filter to default |
| `/profile` (PUT) | `No fields provided` | 400 | "Change something first." |
| any | `Rate limit exceeded` | 429 | "Too many requests. Wait a moment." |
| any (global handler) | unhandled exception | 500 | "Something went wrong on our end. Please try again." |

**Client rule:** unknown status codes fall back to the 500 message; unknown `detail` shapes normalize to a safe string (§9.5). The app **never** crashes on an unexpected response.

## 20. GDPR & privacy compliance (biometric data)

> Face photos + scores are **biometric data** — "special category" personal data (GDPR Art. 9), the highest protection class. This is the compliance plan; build it *with* the features, not after launch.

### 20.1 Legal basis
- Face images = biometric data → processing is **prohibited unless a legal basis applies**. Ours = **explicit consent** (Art. 6(1)(a) + 9(2)(a)) — freely given, specific, informed, unambiguous, and **withdrawable anytime**.
- Derived scores are personal data too, but the *raw image* is the sensitive part.
- **Minors:** body-image content + biometrics → **minimum age 16** (or 13 with verified parental consent). Collect age at signup; reject under-age.
- **Cookies/ePrivacy:** no third-party trackers (§17) → minimal cookie burden; any future cookie/tracking needs a consent banner.

### 20.2 Data inventory (what we hold, why, how long)
| Data | Category | Purpose | Lawful basis | Retention |
|---|---|---|---|---|
| Email | personal | login | contract/consent | account lifetime |
| Hashed password | sensitive | auth | contract | account lifetime |
| **Face photo** | **biometric** | scoring | **explicit consent** | until delete / 30-day auto-purge |
| Feature scores | personal | result/plan | consent | account lifetime |
| Action plan | personal | plan | consent | account lifetime |
| Payment data | financial | billing | contract | per Stripe policy |
| IP / logs | personal | rate-limit/security | legitimate interest | 90 days |

### 20.3 Consent capture (build into signup + upload)
- **Unticked** checkbox at signup: *"I consent to LookMaxx analyzing my photo to generate scores and a plan. I can withdraw this anytime in Settings."*
- **Separate unticked** checkbox: *"Feature my (blurred) transformation in Explore."* Default **off**.
- Record consent **version + timestamp** (a `consent_log` table) so you can prove *when* and *what* was consented.
- First upload shows a one-line reminder of what happens to the photo before it proceeds.

### 20.4 Sub-processors & transfers (DPA table)
| Sub-processor | Touches | Region | Transfer mechanism |
|---|---|---|---|
| Cloudinary | face images | US | SCCs |
| **DeepSeek** | **scores only — never the photo** | China | SCCs + minimization |
| Stripe | payments | US | SCCs |
| Render | app + DB host | US | SCCs |
| Vercel | frontend | US | SCCs |
| Redis (Upstash) | rate-limit counters | US | SCCs |

**Minimization rule:** DeepSeek receives only numeric feature scores + goals, **never the face image** — so the biometric never leaves our control. If a China transfer is unacceptable, fall back to the deterministic rule-based plan generator (already specced).

### 20.5 Privacy by design / default
- Collect only email + optional profile + photo + scores. No location, contacts, or social graph.
- Photos **private by default**; Explore is **opt-in + blurred** (fixes the §5.11 raw-URL finding).
- Server processes the face; the client holds only the result. No third-party ads/trackers (aligns with CSP §5.7).

### 20.6 Data subject rights (Art. 15–22) — build into Settings
- **Access / Portability:** "Export my data" → JSON/zip of profile + scores + plan.
- **Rectification:** edit profile (`PUT /profile`).
- **Erasure:** "Delete my account" → cascade DB delete **+ Cloudinary image purge** (`DELETE /profile/delete` extended); two-step typed confirm.
- **Withdraw consent / restriction / objection:** "Stop processing" = delete photos, keep account in a restricted state.
- **Automated decision-making (Art. 22):** the score is not a legal/significant decision, but stay transparent — a "How this works" explainer + a human-review contact. Never present the score as medical advice.

### 20.7 Retention & deletion schedule
- **Face photos:** auto-purge after **30 days** unused, or on delete (cron + `DELETE /profile/delete`).
- **Scores/plan:** account lifetime. **Consent log:** 6 years (legal record). **Logs/IP:** 90 days. **Backups:** 30 days.

### 20.8 DPIA + breach response
- **DPIA required** (biometric processing at scale for a body-image-sensitive audience): **drafted** in `docs/DPIA.md` (needs controller sign-off).
- **Breach:** notify the supervisory authority **within 72 h** (Art. 33); notify affected users "without undue delay" if high risk (Art. 34). Runbook: detect → contain (revoke keys, disable feature) → assess → notify → post-mortem.

### 20.9 Required pages & ship-gate
- `/privacy` + `/terms` linked in the footer (copy **drafted** in `docs/PRIVACY_POLICY.md` + `docs/TERMS_OF_SERVICE.md`); consent at signup (§20.3); Settings for export/delete/withdraw.
- [ ] Privacy Policy + Terms live, linked in footer
- [ ] Unticked consent checkboxes + `consent_log` (version + timestamp)
- [ ] Explore is opt-in + blurred (no raw face URLs)
- [ ] `DELETE /profile/delete` purges Cloudinary images
- [ ] Export-my-data endpoint works
- [ ] 30-day photo auto-purge cron
- [ ] DPIA documented
- [ ] DPA/SCC notes for each sub-processor
- [ ] Age gate (16+) at signup
- [ ] Logs redact faces/tokens/emails

---

## 21. Production operations & scaling (caching, load balancing, observability)

A screen ships when §19 is satisfied; the **product** is production-ready only when this section is too.

### 21.1 Caching (multi-layer)
- **CDN / static:** content-hashed assets + immutable `Cache-Control` via Vercel edge; Cloudinary `f_auto,q_auto` + long cache.
- **Edge cache (public reads only):** `/health`, product lists, marketing pages. `GET /explore` may be edge-cached **only after** the §20 blur/opt-in fix — until then `Cache-Control: private, no-store` (it returns personal images).
- **Redis (server):** cache the plan (`plan:{user_id}`, TTL 15 min, invalidated on check-in/re-analysis) and product lists (TTL 5 min); reuse the rate-limit instance.
- **Client (TanStack Query):** `staleTime` per entity (profile 5 min, plan 1 min, products 10 min), optimistic check-ins, refetch-on-focus for streaks.
- **Invalidation rule:** every mutation invalidates its related keys (`POST /plan/checkin` → `plan:*`, `dashboard`, `streak`). **Gating reads (`/auth/me`, entitlements) are always live — never cached.**

### 21.2 Load balancing & horizontal scaling
- **Frontend:** Vercel auto-balances serverless functions + serves static on the edge.
- **Backend (Render):** start at 1 worker (512 MB); scale instances → Render load-balances in front.
- **Statelessness is the enabler:** JWT (no server sessions) + Redis (no in-memory state) → **any instance serves any request — no sticky sessions.** Never store session/rate-limit/plan state in process memory.
- **Health checks:** expose `/health` (liveness) + `/health/ready` (readiness: model loaded, DB reachable) so the LB routes only to healthy instances.
- **ML isolation:** move inference to a queue worker (Celery + Redis / Render background worker) so a slow analysis never starves the API (§14.3).

### 21.3 Observability & monitoring
- **Structured logs:** JSON with `request_id`, hashed `user_id`, `route`, `status`, `latency_ms`; **redact** emails, tokens, and never log face URLs.
- **Metrics:** p50/p95 latency, error rate, analysis queue depth, paywall 403 rate, upload success rate.
- **Error tracking:** Sentry (backend + frontend) with PII scrubbing on.
- **Uptime:** external uptime check + alerts on error-rate spike or queue backlog.

### 21.4 Backups, CI/CD, secrets, cost
- **Backups:** Render daily Postgres backups (point-in-time); one restore drill (RPO 24 h / RTO < 1 h for V1).
- **CI/CD:** dev → staging → prod; lint + typecheck + tests on every PR; deploy on merge to `main`; Alembic migrations with rollback (test on a staging clone first); Vercel/Render preview deploys.
- **Secrets:** per-environment env vars (never in git); rotation plan for `SECRET_KEY` (invalidates tokens — pair with a release), Stripe keys, Cloudinary API secret.
- **Cost:** caching moves load onto free CDN/edge; budget alerts on Render/Vercel/Cloudinary/DeepSeek; rate limiter + free-tier analysis cap stop abuse-driven bill spikes.

### 21.5 Production ship-gate
- [ ] `/health` + `/health/ready` exposed + uptime monitor on
- [ ] Structured logs + Sentry with PII scrubbing
- [ ] Redis cache for plan/products with invalidation wired
- [ ] `/explore` private until the §20 blur/opt-in fix ships
- [ ] Postgres backups enabled + one restore drill done
- [ ] CI runs lint + typecheck + tests on every PR; deploys on merge
- [ ] Secrets per-environment + rotation plan
- [ ] Budget alerts on all paid services

---

*End of specification.*
