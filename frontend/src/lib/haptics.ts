/**
 * Haptics — small, deliberate, and never surprising.
 *
 * Web vibration is Android-only (`navigator.vibrate`); iOS Safari ignores it
 * entirely, which is fine by design — this is *reinforcement*, never the only
 * signal a user gets. It is gated twice:
 *
 *   1. `navigator.userActivation.hasBeenActive` — Chrome refuses (and logs a
 *      warning about) vibration before the user has touched the frame, so a
 *      landing page's decorative animation can never buzz a stranger's phone.
 *   2. `prefers-reduced-motion: reduce` — someone who asked the OS for calm
 *      gets calm in every channel we control, not just visually.
 *
 * Patterns stay ≤ 26ms so they read as a "tick", not as a notification, and
 * every call is wrapped: feedback must never be able to break a tap.
 */
const HAPTICS_MEDIA = "(prefers-reduced-motion: reduce)";

function allowed(): boolean {
  if (typeof navigator === "undefined") return false;
  if (typeof navigator.vibrate !== "function") return false;
  // Older browsers have no `userActivation`: treat "unknown" as allowed — the
  // call itself is a no-op without a user gesture.
  if (navigator.userActivation && navigator.userActivation.hasBeenActive === false) {
    return false;
  }
  if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
    return !window.matchMedia(HAPTICS_MEDIA).matches;
  }
  return true;
}

function buzz(pattern: number | number[]): void {
  if (!allowed()) return;
  try {
    navigator.vibrate(pattern);
  } catch {
    /* blocked or unsupported — never let feedback break the interaction */
  }
}

export const haptics = {
  /** Contact feedback for a press; fires on pointer-down so it feels causal. */
  tick: () => buzz(8),
  /** A confirmed, earned outcome — a saved change, a score landing. */
  success: () => buzz([12, 40, 18]),
  /** A real milestone (Day 7/30/60/90). Reserved for peaks so it stays special. */
  celebrate: () => buzz([16, 60, 16, 60, 26]),
};
