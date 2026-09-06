# Defects & Findings — LookMaxx

> Running log of every defect/finding discovered, triaged, and (where fixed)
> regression-covered during this pass. Severity model: P0 critical / P1 high /
> P2 medium / P3 low.

## FIXED this pass

| ID | Severity | Description | Fix | Regression test |
|---|---|---|---|---|
| DEF-001 | P2 (a11y) | Signup consent "Terms"/"Privacy Policy" inline links had 1.2:1 contrast vs surrounding muted text (axe `link-in-text-block`, needs 3:1 or a non-color indicator). | Added `underline underline-offset-2` to both links in `SignupForm.tsx`. | e2e/accessibility.spec.ts (signup) |
| DEF-002 | P3 | `GET /health` reported a nonsensical `max_rss_mb` (~140880) on macOS — `_get_memory_usage` treated all POSIX as Linux (KB) but macOS reports `ru_maxrss` in bytes. | Platform-aware divisor (`darwin` → bytes/1024², else KB/1024). | manual curl + no regression in test_health |
| DEF-003 | P3 | E2E suite's cumulative anonymous traffic tripped the (correct) 60/min anonymous rate limit, causing spurious 429s that masked 401/200 in unrelated tests. | Made `ANONYMOUS_LIMIT`/`AUTHENTICATED_LIMIT` env-overridable (`RATE_LIMIT_*`); E2E runs with `RATE_LIMIT_ANONYMOUS=1000`. Production defaults unchanged. | e2e/security-headers.spec.ts, auth.spec.ts |
| DEF-004 | P2 (security) | `npm audit` flagged 2 vulns (1 high, 1 moderate) — `postcss@8.4.31` bundled inside `next` (XSS via unescaped `</style>`; arbitrary file read via `sourceMappingURL`). Build-time only; no untrusted CSS input. | Non-breaking fix: npm `overrides` pinning `next → postcss` to patched `8.5.27` (root devDep resolves to `8.5.28`). Avoids the breaking `next@16` upgrade. `npm audit` → 0 vulns. | `npm audit` + production build + full Chromium E2E (43 passed) |

## OPEN (deferred / known)

| ID | Severity | Description | Status |
|---|---|---|---|
| DEF-005 | P3 | 653 deprecation warnings in backend (`datetime.utcnow()`, Pydantic class-config). Cosmetic; migrate to timezone-aware datetimes / `ConfigDict` opportunistically. | OPEN (pre-existing) |
| DEF-006 | P3 | Rate limiter + login throttle are in-memory (per-worker, reset on restart). Correct for single-instance; needs Redis-shared state for horizontal scale. | OPEN (pre-existing, documented in CONTEXT.md) |

## Limitations (not performed — honest)

- **pip-audit**: NOT run — the backend `.venv` has no `pip` module and pip-audit is not installed. Python deps are pinned in `requirements.txt`; a proper OSV/pip-audit scan is a recommended follow-up.
- **OWASP ZAP / DAST**: NOT configured (not installed). Manual HTTP checks (headers, CORS, throttle, information-disclosure) used as the available alternative.
- **CodeQL**: NOT configured (repo has no `.github/workflows`).
- **k6 load testing**: NOT installed; performance checks limited to load-time/latency observation.
- **Interactive Playwright MCP exploration**: NOT possible in this chat session (MCP tools absent); automated Playwright CLI E2E used instead.
