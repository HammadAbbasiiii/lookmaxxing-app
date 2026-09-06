# Discovered Workflows — LookMaxx

> Phase 5/34 deliverable. Workflows observed/verified through automated browser
> interaction this pass (Playwright CLI; interactive MCP unavailable in this
> session).

## WF-01 — Signup (weak password rejection)
- START: `/signup` (anonymous).
- ACTIONS: type `password123` → meter shows "Too common" → fill valid email, tick consent → "Create account".
- EXPECTED: rejected before any API call; error "That password is too common…".
- ACTUAL: matches. Client Zod mirrors backend exactly.
- AUTOMATION: e2e/auth.spec.ts (PASS).

## WF-02 — Signup (valid) → auto-login → onboarding
- START: `/signup`.
- ACTIONS: valid email + strong password + consent → submit.
- EXPECTED: account created, token stored, land on `/onboarding`.
- ACTUAL: matches.
- AUTOMATION: e2e/auth.spec.ts (PASS).

## WF-03 — Signup duplicate
- START: `/signup` with an already-registered email.
- EXPECTED: "That email is already registered. Log in instead."
- ACTUAL: matches.
- AUTOMATION: e2e/auth.spec.ts (PASS).

## WF-04 — Login (wrong password, anti-enumeration)
- EXPECTED: identical "Incorrect email or password." copy for unknown email vs wrong password.
- ACTUAL: matches (single copy path).
- AUTOMATION: e2e/auth.spec.ts (PASS).

## WF-05 — Login throttle
- START: 10 wrong-password attempts (one email) → 11th blocked.
- EXPECTED: 401 ×10 then 429 "Too many failed attempts".
- ACTUAL: matches.
- AUTOMATION: e2e/auth.spec.ts (PASS).

## WF-06 — Route guard / 401
- START: `/dashboard` anonymous → redirect `/login?next=…`.
- START: `/dashboard` with invalid token → token cleared, redirect `/login`.
- ACTUAL: matches.
- AUTOMATION: e2e/unauthorized.spec.ts (PASS).

## WF-07 — Momentum pages (authed)
- START: authed user → `/arc`, `/glow`, `/glowups`, `/dashboard`.
- EXPECTED: render with no uncaught JS errors.
- ACTUAL: matches across Chromium/Firefox/WebKit.
- AUTOMATION: e2e/pages.spec.ts (PASS, @critical).

## WF-08 — Security headers / CORS
- EXPECTED: hardening headers on 200/401/429; CORS allows `localhost:3000`, rejects unlisted origin.
- ACTUAL: matches.
- AUTOMATION: e2e/security-headers.spec.ts (PASS).

## WF-09 — Password visibility toggle (keyboard)
- START: `/signup`, focus "Show password" button → Enter → input type flips to text.
- ACTUAL: matches.
- AUTOMATION: e2e/accessibility.spec.ts (PASS).

## Not yet automated (upload→analysis→results, payments)
- Requires Cloudinary + real image upload; deferred (documented in TEST-MATRIX as FLOW-01 ⬜).
