"use client";

import { ScoreRing } from "@/components/ui/ScoreRing";
import { scoreLabel } from "@/lib/constants";

/**
 * Hero score-reveal teaser (§8.1). Counts up once on mount; static for
 * `prefers-reduced-motion`. No infinite loop.
 */
export function ScoreTeaser() {
  return (
    <section className="border-y border-border-soft bg-surface/40 py-14">
      <div className="mx-auto flex max-w-5xl flex-col items-center gap-8 px-4 md:flex-row md:justify-center md:gap-16">
        <ScoreRing score={84} size={190} label={scoreLabel(84)} />
        <div className="max-w-xs text-center md:text-left">
          <p className="text-sm text-muted">Your baseline</p>
          <p className="font-display text-4xl font-bold tabular">71</p>
          <p className="mt-3 text-sm text-muted">Your potential</p>
          <p className="font-display text-4xl font-bold text-gold tabular">84</p>
          <p className="mt-4 text-sm text-muted">
            Up to <span className="text-gold-bright">+13 points</span> with a
            consistent 90-day plan.
          </p>
        </div>
      </div>
    </section>
  );
}
