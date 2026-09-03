"use client";

import Link from "next/link";
import { ArrowRight, Lock, Sparkles } from "lucide-react";
import type { FutureSelfMessage, PeakYou } from "@/lib/peak";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { CategoryBar } from "@/components/ui/CategoryBar";
import { Badge } from "@/components/ui/Badge";
import { scoreLabel } from "@/lib/constants";
import { formatScore } from "@/lib/utils";

/** Free-user hook: two versions of you — one stays, one ascends (locked). */
export function TwoFutures({ currentScore }: { currentScore: number }) {
  return (
    <div className="rounded-card card-border p-5">
      <h3 className="font-display text-base font-semibold text-ink">Two versions of you exist.</h3>
      <p className="mt-1 text-sm text-muted">The only difference between them is the next 90 days.</p>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-lg bg-surface-2 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">If you stop</p>
          <p className="mt-2 font-display text-3xl font-bold text-muted">{formatScore(currentScore)}</p>
          <p className="mt-1 text-xs text-muted">stays here</p>
        </div>
        <div className="relative overflow-hidden rounded-lg gold-gradient p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-black/60">If you ascend</p>
          <p className="mt-2 select-none font-display text-3xl font-bold text-black blur-[6px]" aria-hidden>
            95
          </p>
          <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-black/10 px-2 py-0.5 text-[11px] font-semibold text-black">
            <Lock className="h-3 w-3" aria-hidden /> Unlock
          </span>
        </div>
      </div>

      <Link href="/upgrade" className="mt-4 inline-block">
        <span className="gold-gradient inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-black">
          <Sparkles className="h-3.5 w-3.5" aria-hidden /> See your peak
        </span>
      </Link>
    </div>
  );
}

/** Pro: the full reveal — now → peak, the ascent, levers, and who you're becoming. */
export function PeakYouReveal({ peak }: { peak: PeakYou }) {
  return (
    <div className="space-y-4">
      <div className="rounded-card card-border p-6 text-center">
        <p className="text-[11px] font-semibold uppercase tracking-widest text-gold">Your potential</p>
        <div className="mt-4 flex justify-center">
          <ScoreRing score={peak.peak} size={176} label={scoreLabel(peak.peak)} />
        </div>
        <div className="mt-4 flex items-center justify-center gap-2">
          <span className="text-sm text-muted">{formatScore(peak.now)} today</span>
          <ArrowRight className="h-4 w-4 text-gold" aria-hidden />
          <span className="font-display text-lg font-bold text-gold-bright">{formatScore(peak.peak)}</span>
        </div>
        <p className="mt-1 text-sm text-muted">
          <span className="font-semibold text-success">+{peak.delta} points</span> in {peak.daysRemaining || 90} days —
          the only difference is showing up.
        </p>
        {peak.rankLabel ? (
          <p className="mt-2 text-xs text-muted">
            {peak.rankLabel} now
            {peak.percentile != null ? (
              <>
                {" "}— you beat <span className="font-semibold text-ink">{peak.percentile}%</span> of{" "}
                {peak.peerCount} peers. At peak you join the top tier.
              </>
            ) : (
              <> — at peak you join the top tier.</>
            )}
          </p>
        ) : null}
      </div>

      <div className="rounded-card card-border p-5">
        <h3 className="text-sm font-semibold text-ink">Your ascent</h3>
        <div className="mt-3 grid grid-cols-3 gap-2">
          {peak.milestones.map((m) => (
            <div key={m.day} className="rounded-lg bg-surface-2 p-3 text-center">
              <div className="text-xs text-muted">Day {m.day}</div>
              <div className="mt-1 font-display text-xl font-bold text-ink">{formatScore(m.projected_score)}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-card card-border p-5">
        <div className="flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-ink">Your levers</h3>
          {peak.biggestLever ? <Badge variant="warning">{peak.biggestLever.label} = biggest lever</Badge> : null}
        </div>
        <div className="mt-3 space-y-3">
          {peak.categories.map((c) => (
            <div key={c.key}>
              <CategoryBar label={c.label} value={c.now} />
              <p className="mt-0.5 text-right text-[11px] text-muted">→ {c.peak} projected</p>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-card card-border p-5">
        <h3 className="text-sm font-semibold text-ink">Who you&apos;re becoming</h3>
        <p className="mt-2 font-display text-lg font-semibold text-ink">
          {peak.archetype.emoji} {peak.archetype.name}
        </p>
        <p className="mt-1 text-sm text-muted">{peak.archetype.vibe}</p>
      </div>
    </div>
  );
}

/** Elite: the daily message from the person you're becoming. */
export function FutureSelfCard({ message }: { message: FutureSelfMessage }) {
  return (
    <div className="mt-4 rounded-card card-border p-5">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-full bg-gold/15 text-lg" aria-hidden>
          {message.emoji}
        </span>
        <div>
          <p className="text-sm font-semibold text-ink">{message.from}</p>
          <p className="text-xs text-muted">
            {message.name} · Day {message.day}
          </p>
        </div>
      </div>
      <p className="mt-3 text-sm leading-relaxed text-ink">{message.text}</p>
    </div>
  );
}
