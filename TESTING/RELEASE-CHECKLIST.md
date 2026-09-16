# Release Checklist — LookMaxx

> Pre-release verification gates. Each item maps to a test/artifact.

## Automated (this pass)
- [x] Backend pytest: 261 passed, 0 failed.
- [x] Frontend typecheck (`tsc --noEmit`): clean.
- [x] Frontend production build: (see TEST-RESULTS.md for build status).
- [x] E2E Chromium: 43 passed (auth, momentum pages, security headers, CORS, 401/route-guard, responsive ×8 viewports, a11y, visual captures).
- [x] E2E cross-browser critical (Firefox + WebKit): 18 passed.
- [x] Accessibility: axe 0 critical/serious on login/signup/dashboard.
- [x] Security headers on 200/401/429 + CORS allow-list verified over HTTP.
- [x] Information disclosure: no password hash in signup response.
- [x] Login throttle (10/15min) + rate limiting verified.

## Manual / evidence
- [x] Visual evidence captured (TESTING/screenshots/).
- [x] Dependency audit: npm audit — 0 vulnerabilities (postcss overridden, see DEFECTS.md DEF-004).
- [ ] pip-audit (NOT RUN — no pip in venv).
- [ ] OWASP ZAP DAST (NOT RUN).
- [ ] CodeQL (NOT configured).
- [ ] k6 load test (NOT RUN).
- [ ] Interactive Playwright MCP exploration (unavailable this session).

## Deploy gates (production)
- [x] `SECRET_KEY` code-hardened: `config.py` now raises in production for the default key OR any key < 32 chars. Local `.env` already holds a 64-char key. → **Still required: set that strong key in the Render env var (not the local `.env`).**
- [x] `CORS_ORIGINS` code-tightened: production no longer falls back to localhost origins — only `FRONTEND_URL` + explicit `CORS_ORIGINS`. → **Still required: set `FRONTEND_URL` to the real frontend origin in Render.**
- [x] Redis is live in production: `GET /api/v1/health` returns `"redis":"connected"`, so `REDIS_URL` is set and rate limiting is not silently falling back to in-memory.
- [ ] **`DATABASE_URL` — confirm it is a `postgresql://…` URL in the Render dashboard.** `config.py` falls back to `sqlite:///./lookmaxx.db` when the var is empty, and a Render web service has an **ephemeral filesystem**: with the fallback, every deploy silently wipes users, plans and check-ins. `CONTEXT.md` says it is set and `MEMORY.md` says it is missing — one is stale, so verify by eye before launch.
- [ ] Stripe **live** keys + live webhook secret + the 4 live price IDs (while unset, `/payments/checkout` returns an honest `503 payments_unconfigured`).
- [ ] Cloudinary credentials configured — required for uploads; without them no analysis can run.
- [ ] SMTP (`EMAIL_PROVIDER=smtp` + `SMTP_*`) for real reset-link delivery. The default `console` only *logs* the link, so "forgot password" is broken for real users until this is set.
- [ ] `NEXT_PUBLIC_API_URL` set on the frontend host (it already defaults to the Render origin in `constants.ts`, so a missing var still works — belt and braces).
- [x] postcss advisories cleared (DEF-004): non-breaking npm `overrides` → `npm audit` 0 vulns (no Next 16 upgrade needed).

## Go-live runbook (launch day — do these in order)
Order matters: backend env → frontend deploy → CORS → payments → smoke test. The CORS step **must** precede any real user hitting the Vercel URL, or every API call from the browser is blocked.

### 1. Stripe → live mode (~15 min)
1. Stripe dashboard → turn **Test mode off**.
2. **Products** → create 4 recurring **GBP** prices matching what the UI displays (`frontend/src/lib/constants.ts`): Pro £9.99/month, Pro £50.40/year, Elite £19.99/month, Elite £100.80/year. Live IDs differ from test IDs — a test `price_…` with a live key fails at checkout.
3. Optional: create the "£1 first month" coupon and set `STRIPE_FIRST_MONTH_COUPON_ID`; `STRIPE_ELITE_TRIAL_DAYS` defaults to 7.
4. **Webhooks** → Add endpoint → `https://lookmaxx-api.onrender.com/api/v1/payments/webhook`, subscribing to exactly the 6 events the handler implements: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`. Copy the endpoint's signing secret (`whsec_…`).
5. Render → `lookmaxx-api` → **Environment** → set `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRICE_PRO_ANNUAL`, `STRIPE_PRICE_ELITE_MONTHLY`, `STRIPE_PRICE_ELITE_ANNUAL` → Save (Render redeploys).
   `STRIPE_PUBLISHABLE_KEY` is **not** needed: Checkout is hosted by Stripe and there is no Stripe.js in the client.
6. Verify live mode (the config check runs *after* auth, so an unauthenticated call is 401 — use a real token):
   ```bash
   TOKEN=…   # deployed app → DevTools → Application → localStorage
   curl -s -X POST https://lookmaxx-api.onrender.com/api/v1/payments/checkout \
     -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
     -d '{"tier":"pro","annual":false}' | grep -o 'cs_[a-z]*_'
   ```
   `cs_live_` → live. `cs_test_` → still test keys. `503 payments_unconfigured` → env vars not picked up.
   Creating a session charges nothing — just don't complete it.

### 2. Frontend → Vercel (~20 min)
1. Vercel → **Add New → Project** → import `HammadAbbasiiii/lookmaxxing-app`.
2. **Root Directory: `frontend`** — the repo has `backend/` and `frontend/` side by side, so Vercel must not build the repo root. Preset: Next.js (`npm run build` / `npm install`).
3. Env var (Production + Preview): `NEXT_PUBLIC_API_URL=https://lookmaxx-api.onrender.com/api/v1`.
4. Deploy, then note the production origin (e.g. `https://lookmaxx.vercel.app`).

### 3. Close the CORS loop (~3 min) — REQUIRED
Render → Environment → set both to the Vercel origin (**exact origin, no trailing slash**):
- `FRONTEND_URL=https://<your-domain>` (also used for reset links and Stripe success/cancel URLs)
- `CORS_ORIGINS=https://<your-domain>` (comma-separate extras; there is no wildcard support, and Vercel *preview* URLs change per deploy)

Save → wait for the redeploy → then open the site. Symptom of skipping this: the page loads but every API call fails and login appears to do nothing.

### 4. Production smoke test (~15 min, on the deployed URL)
- [ ] Site loads with no console errors and no CORS errors.
- [ ] `GET /api/v1/health` reports `"mediapipe": {"available": true, "model_path_exists": true}` — if `available` is `false`, analyses will honestly report "not measured" instead of scoring anything (DEF-014), so this must be `true` before launch.
- [ ] Sign up with a real email → onboarding reports **"Step 1 of 3"** → upload a photo → a score appears (proves Cloudinary + ML/DeepSeek on prod).
- [ ] Free user: bottom nav shows 5 tabs (Home · Plan · Coach · Glow · Explore); `/glow-up` shows exactly **one** paywall card; Explore's Glow-Ups card opens `/glowups` and its back link returns to Explore.
- [ ] A second upload as a free user shows the "You've used your free analysis" gate (paywall after value, never before).
- [ ] Buy Pro with a real card (live mode has no test cards — use a real card and refund it in Stripe immediately), confirm the redirect lands on `/upgrade/success?session_id=…` and that the receipt shows the **actual** charged amount (the first month is £1.00 with the coupon, then £9.99/month) and the tier flips to Pro.
- [ ] Confirm the first-month price shown **before** paying matches the receipt: `/upgrade` (Monthly) must headline the same amount `GET /payments/offer` returns, and the CTA must read "Start for £1.00" (DEF-015).
- [ ] Stripe → Webhooks → the endpoint shows `200`s for the 6 events, no 4xx/5xx.
- [ ] Cancel from Settings → billing → stays Pro until period end, then drops to free (`customer.subscription.updated` / `deleted` paths).
- [ ] "Forgot password" → the email actually arrives (requires `EMAIL_PROVIDER=smtp`).
- [ ] Sign out in one tab, act in another → redirected to `/login?next=…`.
- [ ] Mobile viewport: no horizontal scroll; tab targets ≥44 px.
- [ ] Render → **Events/Deploys**: the live commit SHA equals `git rev-parse --short HEAD` and the deploy is "live".


## Final decision
See TEST-RESULTS.md "Release status".
