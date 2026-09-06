# Security Plan — LookMaxx

> Phase 19–22 planning + findings. Non-destructive. Local/test env only.

## 1. What already exists (from source + tests)

- Password strength: min 8 chars, 2 of 4 classes, common-password blocklist,
  email-as-password block, **no password strip**.
- bcrypt hashing; HS256 JWT (30-min TTL) with `token_version` revocation.
- Login throttle (10 fails / 15 min / email+IP) + Redis sliding-window rate limit.
- CORS explicit allow-list, `allow_credentials=False`.
- Security headers (backend middleware outermost + Next.js `headers()`).
- Anti-enumeration login + forgot-password (identical responses, timing-equalized).
- Single-use hashed password reset tokens.
- Admin gate: `is_admin` flag OR `ADMIN_EMAILS`.
- IDOR blocked (owner-scoped → 404).
- `test_security.py` + `test_password_reset.py` + `test_password_strength.py` + `test_premium_gating.py`.

## 2. Static analysis

- No CodeQL config present (repo has no `.github/workflows`). **Not configured
  this pass** — documented limitation; recommended next step.
- Manual review performed (see ARCHITECTURE.md weaknesses).

## 3. Dependency audit (this pass)

- `npm audit` (frontend) — run; result recorded in DEFECTS.md.
- Python deps — `pip-audit` if installable; else manual review of pinned versions.

## 4. Dynamic security testing

- Security headers verified over HTTP (E2E) against local backend.
- CORS behavior verified (preflight / disallowed origin).
- Rate limit + login throttle re-verified over HTTP.
- OWASP ZAP: **not configured** (not installed). Documented limitation; manual
  HTTP checks used as the available alternative.

## 5. Out of scope / NOT performed

- No destructive attacks. No production testing. No real credentials used.
- WebSocket/CSRF: not applicable (bearer tokens, no cookies, no sockets).
- File upload path traversal: Cloudinary direct-upload flow; backend validates
  extensions/size. Deep payload fuzzing not performed (no ZAP/Burp).

## 6. Remaining risks (honest)

- In-memory rate limit/login throttle do not scale horizontally (per-worker).
- `/upload/save` trusts Cloudinary URL by cloud-name substring.
- Stripe/webhook only honest-fails (503) until real keys are configured and
  exercised against Stripe test mode.
