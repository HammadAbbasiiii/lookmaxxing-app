# Performance Plan — LookMaxx

> Phase 25. Targets derived from PRODUCT_SPEC §21 where available; otherwise
> reasonable engineering thresholds documented explicitly (not invented as
> "requirements").

## 1. Performance-critical operations

- Page load (landing, dashboard, momentum pages).
- API latency (health, /auth/me, /dashboard, /arc/state, /glow/state, /glowups/feed).
- Photo upload/analysis (Cloudinary + lazy ML) — heavy; not load-tested this pass.
- DeepSeek AI calls — has 8s timeout + deterministic fallback.

## 2. This pass

- Measure page load + key API latency via Playwright (soft thresholds, recorded
  not enforced as pass/fail).
- No dedicated load tool (k6) installed — **documented limitation**.

## 3. Thresholds (engineering, documented)

- Landing `/` TTFB < 3s, dashboard < 5s on local dev (Next dev is slower than prod).
- `/health` < 500ms local.
- Momentum read endpoints < 2s local (SQLite).

## 4. Not performed

- Load/stress/sustained load (k6 not installed).
- Database query profiling (EXPLAIN) under load.
- Memory/CPU monitoring under concurrency.
