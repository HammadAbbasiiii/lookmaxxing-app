"use client";

import { Crown, Share2, TrendingUp, Trophy } from "lucide-react";
import type { Harmony, Insights } from "@/lib/zod";
import { cn, formatScore } from "@/lib/utils";
import { shareText } from "@/lib/share";
import { Skeleton } from "@/components/ui/Skeleton";
import { CategoryBar } from "@/components/ui/CategoryBar";

export function InsightsSection({ insights, loading }: { insights?: Insights; loading: boolean }) {
  if (loading) return <Skeleton className="mt-6 h-44 w-full rounded-card" />;
  if (!insights) return null;
  const { forecast, percentile, archetype } = insights;

  return (
    <div className="mt-6 space-y-4">
      <div className="flex items-center gap-2">
        <TrendingUp className="h-4 w-4 text-gold" aria-hidden />
        <h2 className="font-display text-lg font-semibold text-ink">Glow-Up insights</h2>
      </div>

      <div className="rounded-card card-border p-5">
        <p className="text-sm text-muted">{forecast.headline}</p>
        <div className="mt-3 grid grid-cols-3 gap-2">
          {forecast.milestones.map((m) => (
            <div key={m.day} className="rounded-lg bg-surface-2 p-3 text-center">
              <div className="text-xs text-muted">Day {m.day}</div>
              <div className="mt-1 font-display text-xl font-bold text-ink">
                {formatScore(m.projected_score)}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-card card-border p-5">
          <div className="flex items-center gap-2 text-gold-bright">
            <Trophy className="h-4 w-4" aria-hidden />
            <h3 className="text-sm font-semibold">Your rank</h3>
          </div>
          <p className="mt-2 font-display text-2xl font-bold text-ink">{percentile.rank_label}</p>
          <p className="mt-1 text-xs text-muted">
            {percentile.percentile == null
              ? "Your rank unlocks as more people analyze their photos."
              : percentile.peer_count < 10
                ? "Not enough peers yet to rank you fairly."
                : `You beat ${percentile.percentile}% of ${percentile.peer_count} peers.`}
          </p>
        </div>

        <div className="rounded-card card-border p-5">
          <h3 className="text-sm font-semibold text-ink">
            {archetype.emoji} {archetype.name}
          </h3>
          <p className="mt-1 text-sm text-muted">{archetype.vibe}</p>
          {archetype.reasons.length ? (
            <ul className="mt-2 space-y-1 text-xs text-muted">
              {archetype.reasons.map((r, i) => (
                <li key={i}>✓ {r}</li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/**
 * Elite harmony block. `showCard` is false on /results, where the shareable card
 * renders beside the score ring instead — the moment of peak emotion — rather
 * than ~80% down the page.
 */
export function HarmonySection({
  harmony,
  loading,
  showCard = true,
}: {
  harmony?: Harmony;
  loading: boolean;
  showCard?: boolean;
}) {
  if (loading) return <Skeleton className="mt-6 h-44 w-full rounded-card" />;
  if (!harmony) return null;
  const { golden_ratio, blueprint, glow_up_card } = harmony;

  return (
    <div className="mt-6 space-y-4">
      <div className="flex items-center gap-2">
        <Crown className="h-4 w-4 text-gold" aria-hidden />
        <h2 className="font-display text-lg font-semibold text-ink">Elite harmony</h2>
      </div>

      <div className="rounded-card card-border p-5">
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="text-sm font-semibold text-ink">Golden-ratio map</h3>
          {golden_ratio.phi_score != null ? (
            <span className="font-display text-2xl font-bold text-gold-bright">
              {formatScore(golden_ratio.phi_score)}
            </span>
          ) : null}
        </div>
        <p className="mt-1 text-xs text-muted">{golden_ratio.summary}</p>
        <div className="mt-3 space-y-2">
          {golden_ratio.metrics.map((m) => (
            <CategoryBar key={m.key} label={m.label} value={m.score} />
          ))}
        </div>
      </div>

      <div className="rounded-card card-border p-5">
        <h3 className="text-sm font-semibold text-ink">{blueprint.week_label}</h3>
        <p className="mt-1 text-xs text-muted">{blueprint.gender_note}</p>
        <ul className="mt-3 space-y-2">
          {blueprint.days.map((d) => (
            <li key={d.day} className="flex items-start gap-2 text-sm">
              <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gold/15 text-xs font-semibold text-gold">
                {d.day}
              </span>
              <span className="text-muted">
                <span className="font-medium text-ink">{d.focus}:</span> {d.task}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {showCard ? <GlowUpShareCard card={glow_up_card} /> : null}
    </div>
  );
}

/**
 * The Elite shareable card: headline, score, archetype/strength/day and the
 * caption you'd post it with. Rendered beside the score ring on /results (the
 * emotional peak) and inside the harmony block on /glow-up — one component, so
 * the two surfaces can't drift apart.
 */
export function GlowUpShareCard({
  card,
  className,
}: {
  card: Harmony["glow_up_card"];
  className?: string;
}) {
  return (
    <div className={cn("rounded-card gold-gradient p-5 text-black", className)}>
      <p className="text-xs font-semibold uppercase tracking-wide">{card.headline}</p>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="font-display text-4xl font-bold">{formatScore(card.score)}</span>
        <span className="text-sm font-medium">{card.label}</span>
      </div>
      <p className="mt-1 text-sm">
        {card.archetype} · {card.top_strength} · Day {card.day}
      </p>
      <p className="mt-2 text-xs opacity-80">{card.share_text}</p>
      <button
        type="button"
        onClick={() => shareText(card.share_text, { copied: "Glow-Up card copied to clipboard" })}
        className="mt-3 inline-flex items-center gap-2 rounded-lg bg-black px-3 py-2 text-sm font-semibold text-gold transition-colors hover:bg-black/85 active:scale-[0.98]"
      >
        <Share2 className="h-4 w-4" aria-hidden />
        Share card
      </button>
    </div>
  );
}

