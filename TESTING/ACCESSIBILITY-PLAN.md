# Accessibility Plan — LookMaxx

> Phase 14. Automated axe + manual keyboard checks. NOT a WCAG compliance claim.

## 1. Automated (axe-core)

Targets:
- `/login`, `/signup` (form labels, accessible names, contrast, landmarks).
- `/dashboard`, `/arc`, `/glow`, `/glowups` (authed, after login).

Implemented in `frontend/e2e/accessibility.spec.ts` using `@axe-core/playwright`.
Pass criteria: **0 critical** + **0 serious** violations on scanned pages.
Moderate/minor findings are logged and reviewed, not silently waived.

## 2. Manual keyboard checks (this pass)

- Tab order on login/signup.
- Password show/hide toggle is keyboard-operable (Enter/Space).
- Submit via Enter key.
- Focus visibility.

## 3. Already present in code

- `MotionConfig reducedMotion="user"` (respects prefers-reduced-motion).
- lucide icons with aria-hidden where decorative; text labels for controls.
- Semantic HTML (Next.js) + form labels.

## 4. Known limitations

- axe is automated; it cannot prove WCAG conformance.
- Color-contrast is only partially detectable (depends on rendering).
- Screen-reader (VoiceOver/NVDA) pass NOT performed — documented limitation.
- Full keyboard-only traversal of every screen NOT exhaustively performed this
  pass (login/signup/dashboard covered; deeper app screens partial).
