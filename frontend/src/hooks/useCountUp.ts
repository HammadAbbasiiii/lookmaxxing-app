"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Animated count-up for score reveals. Respects `prefers-reduced-motion`
 * (falls back to the final value instantly, §6.4).
 *
 * `onLand` fires exactly once, the moment the number reaches its target —
 * including on the instant, reduced-motion path — so callers can hang the
 * landing beat (flare, pop, haptic) off it without caring which path ran. The
 * callback is held in a ref: callers pass an inline arrow, and a changing
 * dependency would otherwise restart the count on every parent render.
 */
export function useCountUp(
  target: number,
  durationMs = 1200,
  onLand?: () => void,
): number {
  const [value, setValue] = useState(0);
  const rafRef = useRef<number>(0);
  const onLandRef = useRef(onLand);

  useEffect(() => {
    onLandRef.current = onLand;
  }, [onLand]);

  useEffect(() => {
    let landed = false;
    const land = () => {
      if (landed) return;
      landed = true;
      onLandRef.current?.();
    };

    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reduced) {
      setValue(target);
      land();
      return;
    }

    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      setValue(Math.round(target * eased));
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        land();
      }
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, durationMs]);

  return value;
}
