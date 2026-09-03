"use client";

import { useEffect, useState } from "react";
import { clamp, cn } from "@/lib/utils";

interface CategoryBarProps {
  label: string;
  value: number | null | undefined;
  delayMs?: number;
}

/** Animated per-category score bar (§6.4 — animate width on mount). */
export function CategoryBar({ label, value, delayMs = 0 }: CategoryBarProps) {
  const [mounted, setMounted] = useState(false);
  const pct = clamp(value ?? 0, 0, 100);

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), delayMs);
    return () => clearTimeout(t);
  }, [delayMs]);

  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="text-muted">{label}</span>
        <span className="tabular font-medium text-ink">{value === null || value === undefined ? "—" : Math.round(value)}</span>
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
