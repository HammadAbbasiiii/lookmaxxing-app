"use client";

import { useState } from "react";
import { useCountUp } from "@/hooks/useCountUp";
import { haptics } from "@/lib/haptics";
import { clamp, cn, formatScore } from "@/lib/utils";

interface ScoreRingProps {
  score: number | null | undefined;
  size?: number;
  stroke?: number;
  label?: string;
  /**
   * Play the landing beat — ring pop, one gold flare, then the verdict label
   * 340ms later (see globals.css "the landing"). Default on: this is the
   * product's peak on `/results`, where the whole wait pays off. Pass `false`
   * for a ring that must stay quiet.
   */
  celebrate?: boolean;
}

/**
 * The "wow" score ring: count-up number + gold ring fill (§6.1, §8.7).
 *
 * The reveal is sequenced on purpose — number lands first, meaning second.
 * Showing both at once makes a score read as *printed*; letting the number land
 * and then answering "what does it mean?" is what makes it feel *earned* (§4).
 */
export function ScoreRing({
  score,
  size = 200,
  stroke = 12,
  label,
  celebrate = true,
}: ScoreRingProps) {
  const safe = score ?? 0;
  const [landed, setLanded] = useState(false);
  const display = useCountUp(clamp(safe, 0, 100), 1200, () => {
    setLanded(true);
    // Reinforcement only reaches a phone that has been touched at least once
    // (`haptics` gates on user activation) and only for a real score.
    if (celebrate && score != null) haptics.success();
  });
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamp(display, 0, 100) / 100) * circumference;
  const beat = celebrate && landed;

  return (
    <div
      className={cn(
        "relative inline-flex items-center justify-center",
        beat && "animate-land-pop",
      )}
      style={{ width: size, height: size }}
    >
      {/* One-shot gold flare at the moment the number lands. Decorative and
          `pointer-events-none`, so it can never intercept a tap. */}
      {beat ? (
        <span
          aria-hidden
          className="land-flare animate-land-flare pointer-events-none absolute inset-0 rounded-full"
        />
      ) : null}
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-surface-2)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="url(#goldGradient)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
        <defs>
          <linearGradient id="goldGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--color-gold-bright)" />
            <stop offset="100%" stopColor="var(--color-gold-deep)" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="tabular font-display text-6xl font-bold text-ink leading-none">
          {formatScore(display)}
        </span>
        {label && (!celebrate || landed) ? (
          <span
            className={cn(
              "mt-1.5 text-sm text-muted",
              celebrate && "animate-label-in",
            )}
          >
            {label}
          </span>
        ) : null}
      </div>
    </div>
  );
}

