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
- [ ] Stripe keys + webhook secret + price IDs configured (payments currently honest-fail 503) — requires your Stripe account.
- [ ] Cloudinary credentials configured — requires your Cloudinary account.
- [ ] SMTP (`EMAIL_PROVIDER=smtp`) configured for real reset-link delivery — requires your SMTP provider.
- [ ] Redis configured (rate limiting currently in-memory fallback) — requires your Redis instance.
- [x] postcss advisories cleared (DEF-004): non-breaking npm `overrides` → `npm audit` 0 vulns (no Next 16 upgrade needed).

## Final decision
See TEST-RESULTS.md "Release status".
