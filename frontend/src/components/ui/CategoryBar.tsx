"use client";

import { useEffect, useState } from "react";
import { clamp, cn } from "@/lib/utils";

interface CategoryBarProps {
  label: string;
  value: number | null | undefined;
  delayMs?: number;
  /** Tooltip shown when there is no score — explains *why* (DEF-014). */
  unmeasuredHint?: string;
}

/**
 * Animated per-category score bar (§6.4 — animate width on mount).
 *
 * A score of 0 is never rendered as a measurement: 0 is physically impossible
 * for a real face (a pre-DEF-014 analysis scored synthetic landmarks and clamped
 * to exactly 0), so anything ≤ 0 reads "—" with an explanation instead of a
 * number that looks like a broken result.
 */
export function CategoryBar({
  label,
  value,
  delayMs = 0,
  unmeasuredHint = "Not enough landmark data to measure this.",
}: CategoryBarProps) {
  const [mounted, setMounted] = useState(false);
  const measured = typeof value === "number" && Number.isFinite(value) && value > 0;
  const pct = measured ? clamp(value, 0, 100) : 0;

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), delayMs);
    return () => clearTimeout(t);
  }, [delayMs]);

  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="text-muted">{label}</span>
        {measured ? (
          <span className="tabular font-medium text-ink">{Math.round(value)}</span>
        ) : (
          <span className="font-medium text-muted" title={unmeasuredHint}>
            —
            <span className="sr-only"> not measured. {unmeasuredHint}</span>
          </span>
        )}
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-surface-2">
        <div
          className={cn("h-full rounded-full gold-gradient transition-[width] duration-500 ease-out")}
          style={{ width: mounted ? `${pct}%` : "0%", transitionDelay: `${delayMs}ms` }}
        />
      </div>
    </div>
  );
}
