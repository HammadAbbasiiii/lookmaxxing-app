// "Peak You" — a deterministic, client-side projection of the user's future self.
// Composes data we already fetch (analysis + insights) into an emotional reveal
// without any GenAI/GPU cost. To tune copy/tone, edit the template array below.

import type { Analysis, Insights } from "@/lib/zod";
import { clamp } from "@/lib/utils";

type Archetype = Insights["archetype"];
type Milestone = Insights["forecast"]["milestones"][number];

// Category weights sum to 1 — how the overall potential delta is distributed
// across features. Jawline + skin are the strongest levers for this audience.
export const PEAK_CATEGORIES = [
  { key: "jawline", label: "Jawline", weight: 0.35 },
  { key: "skin", label: "Skin", weight: 0.3 },
  { key: "symmetry", label: "Symmetry", weight: 0.2 },
  { key: "eyes", label: "Eyes", weight: 0.15 },
] as const;

export interface CategoryDelta {
  key: string;
  label: string;
  now: number;
  peak: number;
}

export interface PeakYou {
  now: number;
  peak: number;
  delta: number;
  daysRemaining: number;
  milestones: Milestone[];
  percentile: number | null;
  rankLabel: string;
  peerCount: number;
  archetype: Archetype;
  categories: CategoryDelta[];
  biggestLever: CategoryDelta | null;
  ace: CategoryDelta | null;
}

function scoreAt(analysis: Analysis | undefined, key: string): number {
  const scores = analysis?.scores as Record<string, number | null> | undefined;
  return scores?.[key] ?? 0;
}

export function buildPeakYou(
  analysis: Analysis | undefined,
  insights: Insights | undefined,
): PeakYou | null {
  if (!insights) return null;

  const now = Math.round(insights.forecast.current_score || scoreAt(analysis, "overall"));
  const peak = Math.round(insights.forecast.potential_score || now);
  const delta = Math.max(0, peak - now);

  const categories: CategoryDelta[] = PEAK_CATEGORIES.map((c) => {
    const cur = Math.round(scoreAt(analysis, c.key));
    // Distribute the projected overall gain across features (clearly labeled a projection).
    const proj = clamp(Math.round(cur + delta * c.weight), 30, 97);
    return { key: c.key, label: c.label, now: cur, peak: proj };
  });

  const sorted = [...categories].sort((a, b) => a.now - b.now);

  return {
    now,
    peak,
    delta,
    daysRemaining: insights.forecast.days_remaining,
    milestones: insights.forecast.milestones,
    percentile: insights.percentile.percentile,
    rankLabel: insights.percentile.rank_label,
    peerCount: insights.percentile.peer_count,
    archetype: insights.archetype,
    categories,
    biggestLever: sorted[0] ?? null,
    ace: sorted[sorted.length - 1] ?? null,
  };
}

// "Journey day" = how far along the 90-day ascent the user is (1–90).
export function journeyDay(peak: PeakYou): number {
  return clamp(90 - peak.daysRemaining, 1, 90);
}

export interface FutureSelfMessage {
  from: string;
  name: string;
  emoji: string;
  day: number;
  text: string;
}

const FUTURE_SELF_TEMPLATES = [
  "I remember Day {day}. You almost skipped it. Don't. The work starts compounding this week.",
  "You're at {now}, I'm at {peak}. The gap between us is just reps and consistency — nothing else.",
  "Stop comparing your Day {day} to someone else's Day 300. You're ahead of where I was.",
  "The mirror catches up to the work, not the other way around. Do today's routine.",
  "The version of you that skipped today never got here. You didn't skip. That's why I exist.",
  "Your weakest feature is your biggest lever. Fix it first. It's exactly how I got to {peak}.",
  "Drink the water. Fix the sleep. The routine does the rest. I'm the receipt.",
  "Day {day} looks unremarkable on its own. Stacked 90 times, it becomes me.",
];

// `day` is the journey day (1–90). The message rotates daily (by date) so it
// stays fresh without any backend call — fully deterministic.
export function futureSelfMessage(peak: PeakYou, day: number): FutureSelfMessage {
  const name = peak.archetype.name || "The Ascended";
  const emoji = peak.archetype.emoji || "🔥";
  const rotateKey = Math.floor(Date.now() / 86_400_000);
  const template = FUTURE_SELF_TEMPLATES[rotateKey % FUTURE_SELF_TEMPLATES.length];
  const text = template
    .replace(/\{peak\}/g, String(peak.peak))
    .replace(/\{now\}/g, String(peak.now))
    .replace(/\{day\}/g, String(day));
  return { from: "Your future self", name, emoji, day, text };
}
