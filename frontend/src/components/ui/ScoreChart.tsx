"use client";

import { formatScore } from "@/lib/utils";

interface Point {
  label: string;
  value: number | null;
}

/** Minimal dependency-free SVG line chart for score-over-time (§8.10). */
export function ScoreChart({ points }: { points: Point[] }) {
  const valid = points.filter((p) => p.value != null && !Number.isNaN(p.value));
  if (valid.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted">
        No score data yet.
      </div>
    );
  }

  const w = 320;
  const h = 150;
  const pad = 24;
  const min = Math.min(...valid.map((p) => p.value as number), 30);
  const max = Math.max(...valid.map((p) => p.value as number), 95);
  const range = Math.max(1, max - min);

  const x = (i: number) => pad + (i / Math.max(1, valid.length - 1)) * (w - pad * 2);
  const y = (v: number) => h - pad - ((v - min) / range) * (h - pad * 2);

  const linePath = valid.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i)},${y(p.value as number)}`).join(" ");

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" role="img" aria-label="Score over time">
      {[0, 0.5, 1].map((t) => (
        <line
          key={t}
          x1={pad}
          x2={w - pad}
          y1={pad + t * (h - pad * 2)}
          y2={pad + t * (h - pad * 2)}
          stroke="var(--color-surface-2)"
          strokeWidth={1}
        />
      ))}
      <path
        d={linePath}
        fill="none"
        stroke="var(--color-gold)"
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {valid.map((p, i) => (
        <circle key={i} cx={x(i)} cy={y(p.value as number)} r={3.5} fill="var(--color-gold)" />
      ))}
      <text x={pad} y={h - 4} fill="var(--color-muted)" fontSize={10}>
        {valid[0].label}
      </text>
      <text x={x(valid.length - 1) - 40} y={h - 4} fill="var(--color-muted)" fontSize={10}>
        {valid[valid.length - 1].label}
      </text>
      <text x={pad} y={12} fill="var(--color-gold-bright)" fontSize={11} fontWeight={700}>
        {formatScore(valid[valid.length - 1].value)}
      </text>
    </svg>
  );
}
