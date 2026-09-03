"use client";

import { useCountUp } from "@/hooks/useCountUp";
import { clamp, formatScore } from "@/lib/utils";

interface ScoreRingProps {
  score: number | null | undefined;
  size?: number;
  stroke?: number;
  label?: string;
}

/** The "wow" score ring: count-up number + gold ring fill (§6.1, §8.7). */
export function ScoreRing({ score, size = 200, stroke = 12, label }: ScoreRingProps) {
  const safe = score ?? 0;
  const display = useCountUp(clamp(safe, 0, 100));
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clamp(display, 0, 100) / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
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
        {label ? <span className="mt-1.5 text-sm text-muted">{label}</span> : null}
      </div>
    </div>
  );
}
