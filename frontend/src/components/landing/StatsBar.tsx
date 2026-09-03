"use client";

import { useCountUp } from "@/hooks/useCountUp";

const STATS = [
  { value: 10, suffix: "+", label: "Features analyzed" },
  { value: 90, suffix: "", label: "Day personalised plan" },
  { value: 2, suffix: " min", label: "Daily tasks" },
  { value: 13, prefix: "+", suffix: "", label: "Points of upside" },
];

interface StatItemProps {
  value: number;
  prefix?: string;
  suffix?: string;
  label: string;
}

function StatItem({ value, prefix = "", suffix = "", label }: StatItemProps) {
  const display = useCountUp(value);
  return (
    <div className="text-center">
      <p className="tabular font-display text-3xl font-bold text-ink md:text-4xl">
        {prefix}
        {display}
        {suffix}
      </p>
      <p className="mt-1 text-xs text-muted md:text-sm">{label}</p>
    </div>
  );
}

/** Count-up stat strip. Numbers animate once on scroll into view. */
export function StatsBar() {
  return (
    <section className="border-y border-border-soft bg-surface/40">
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-6 px-4 py-10 md:grid-cols-4">
        {STATS.map((s) => (
          <StatItem key={s.label} {...s} />
        ))}
      </div>
    </section>
  );
}
