# Release Checklist — LookMaxx

> Pre-release verification gates. Each item maps to a test/artifact.

## Automated (this pass)
- [x] Backend pytest: 261 passed, 0 failed.
- [x] Frontend typecheck (`tsc --noEmit`): clean.
- [x] Frontend production build: (see TEST-RESULTS.md for build status).
- [x] E2E Chromium: 39 passed (auth, momentum pages, security headers, CORS, 401/route-guard, responsive ×8 viewports, a11y).
- [x] E2E cross-browser critical (Firefox + WebKit): 18 passed.
- [x] Accessibility: axe 0 critical/serious on login/signup/dashboard.
- [x] Security headers on 200/401/429 + CORS allow-list verified over HTTP.
- [x] Information disclosure: no password hash in signup response.
- [x] Login throttle (10/15min) + rate limiting verified.

## Manual / evidence
- [x] Visual evidence captured (TESTING/screenshots/).
- [x] Dependency audit: npm audit (2 vulns, see DEFECTS.md DEF-004).
- [ ] pip-audit (NOT RUN — no pip in venv).
- [ ] OWASP ZAP DAST (NOT RUN).
- [ ] CodeQL (NOT configured).
- [ ] k6 load test (NOT RUN).
- [ ] Interactive Playwright MCP exploration (unavailable this session).

## Deploy gates (production)
- [ ] `SECRET_KEY` is a strong, non-default value in Render env (config.py raises if default + production).
- [ ] `CORS_ORIGINS` tightened to the real frontend origin(s).
- [ ] Stripe keys + webhook secret + price IDs configured (payments currently honest-fail 503).
- [ ] Cloudinary credentials configured.
- [ ] SMTP (`EMAIL_PROVIDER=smtp`) configured for real reset-link delivery.
- [ ] Redis configured (rate limiting currently in-memory fallback).
- [ ] Next.js 16 upgrade assessed to clear postcss advisories (DEF-004).

## Final decision
See TEST-RESULTS.md "Release status".
