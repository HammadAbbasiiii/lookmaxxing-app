"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Crown, ShoppingBag, Sparkles, TrendingUp, Trophy } from "lucide-react";
import { getAnalysis, getAnalysisHarmony, getAnalysisInsights, getPhotoStatus } from "@/lib/api/endpoints";
import type { Harmony, Insights } from "@/lib/zod";
import { useMe } from "@/hooks/useMe";
import { PaywallLock } from "@/components/ui/PaywallLock";
import { STALE, scoreLabel } from "@/lib/constants";
import { formatScore } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorCard } from "@/components/ui/ErrorCard";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { CategoryBar } from "@/components/ui/CategoryBar";
import { SafeImage } from "@/components/ui/SafeImage";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { ApiError } from "@/lib/api/client";

const CATEGORIES = [
  { key: "symmetry", label: "Symmetry" },
  { key: "skin", label: "Skin" },
  { key: "jawline", label: "Jawline" },
  { key: "eyes", label: "Eyes" },
] as const;

export default function ResultsPage() {
  const params = useParams<{ photo_id: string }>();
  const router = useRouter();
  const photoId = Array.isArray(params.photo_id) ? params.photo_id[0] : params.photo_id;
  const { data: me } = useMe();
  const tier = me?.subscription_tier ?? "free";
  const isFree = tier === "free";
  const isPro = tier === "pro" || tier === "elite";
  const isElite = tier === "elite";

  const analysis = useQuery({
    queryKey: ["analysis", photoId],
    queryFn: () => getAnalysis(photoId),
    staleTime: STALE.analysis,
  });
  const status = useQuery({
    queryKey: ["status", photoId],
    queryFn: () => getPhotoStatus(photoId),
    staleTime: STALE.analysis,
  });
  const insights = useQuery({
    queryKey: ["insights", photoId],
    queryFn: () => getAnalysisInsights(photoId),
    enabled: isPro,
    staleTime: STALE.analysis,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 403) return false;
      return failureCount < 1;
    },
  });
  const harmony = useQuery({
    queryKey: ["harmony", photoId],
    queryFn: () => getAnalysisHarmony(photoId),
    enabled: isElite,
    staleTime: STALE.analysis,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 403) return false;
      return failureCount < 1;
    },
  });

  if (analysis.isLoading) return <ResultsSkeleton />;
  if (analysis.isError) {
    const e = analysis.error;
    const notAnalyzed = e instanceof ApiError && e.status === 404 && /not been analyzed/i.test(e.message);
    return (
      <div className="mx-auto max-w-md pt-10">
        <ErrorCard
          title={notAnalyzed ? "Not analyzed yet" : "Photo not found"}
          message={notAnalyzed ? "This photo hasn't been analyzed yet." : "We couldn't find this photo."}
          onRetry={() => router.push("/dashboard")}
          actionLabel="Back to dashboard"
        />
      </div>
    );
  }

  const a = analysis.data;
  const s = status.data;
  const overall = a?.scores?.overall;
  const potential = s?.potential_score;
  const strengths = s?.strengths ?? [];
  const weaknesses = s?.weaknesses ?? [];

  return (
    <div className="mx-auto max-w-md">
      <ScreenHeader title="Your score" subtitle={scoreLabel(overall ?? 0)} />

      <div className="flex flex-col items-center gap-6 sm:flex-row sm:items-center sm:gap-8">
        <SafeImage src={a?.file_url} alt="Your photo" className="h-40 w-40 rounded-card" />
        <div className="flex flex-col items-center">
          <ScoreRing score={overall} size={180} label={scoreLabel(overall ?? 0)} />
        </div>
      </div>

      {potential != null ? (
        <div className="mt-6 flex items-center justify-center gap-2 rounded-card card-border p-4 text-center">
          <Sparkles className="h-4 w-4 text-gold" aria-hidden />
          <p className="text-sm text-muted">
            You're at <span className="font-semibold text-ink">{formatScore(overall)}</span> — your
            potential is <span className="font-semibold text-gold-bright">~{formatScore(potential)}</span>.
          </p>
        </div>
      ) : null}

      <div className="mt-6 space-y-4 rounded-card card-border p-5">
        <h2 className="font-display text-lg font-semibold text-ink">Breakdown</h2>
        {CATEGORIES.map((c, i) => (
          <CategoryBar key={c.key} label={c.label} value={a?.scores?.[c.key]} delayMs={i * 60} />
        ))}
      </div>

      {isFree ? (
        <>
          <PaywallLock
            className="mt-6"
            title="Your full report"
            teaser="Top 3 fixes · the exact routine · your strongest features ranked — ready to read."
            description="The breakdown is free. The written, coach-grade plan for fixing your weakest areas is Pro."
          />
          <PaywallLock
            className="mt-6"
            title="Glow-Up insights"
            teaser="Glow-Up Forecast · Percentile rank · Look-alike archetype — all based on your face."
            description="Pro unlocks your projected Day-30/60/90 score, where you rank, and the archetype you project."
          />
        </>
      ) : null}

      {isPro ? <InsightsSection insights={insights.data} loading={insights.isLoading} /> : null}

      {isElite ? (
        <HarmonySection harmony={harmony.data} loading={harmony.isLoading} />
      ) : isPro ? (
        <PaywallLock
          className="mt-6"
          title="Elite harmony"
          teaser="Golden-ratio harmony map · 7-day glow-up blueprint · shareable score card."
          description="Elite measures your face against phi (1.618) and hands you a day-by-day blueprint plus a shareable card."
        />
      ) : null}

      {strengths.length || weaknesses.length ? (
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {strengths.length ? (
            <div className="rounded-card card-border p-5">
              <h3 className="text-sm font-semibold text-success">Strengths</h3>
              <ul className="mt-2 space-y-1.5 text-sm text-muted">
                {strengths.slice(0, 4).map((item, i) => (
                  <li key={i}>✓ {item}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {weaknesses.length ? (
            <div className="rounded-card card-border p-5">
              <h3 className="text-sm font-semibold text-warning">Room to grow</h3>
              <ul className="mt-2 space-y-1.5 text-sm text-muted">
                {weaknesses.slice(0, 4).map((item, i) => (
                  <li key={i}>• {item}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="mt-8 space-y-3">
        <Link href="/plan" className="block">
          <Button fullWidth size="lg">
            Get your 90-day plan <ArrowRight className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex gap-3">
          <Link href="/products" className="flex-1">
            <Button variant="secondary" fullWidth>
              <ShoppingBag className="h-4 w-4" /> Recommendations
            </Button>
          </Link>
          <Button variant="ghost" onClick={() => router.push("/dashboard")}>
            Dashboard
          </Button>
        </div>
      </div>

      {s && s.score == null && s.analysis_status !== "failed" ? (
        <p className="mt-4 text-center">
          <Badge variant="warning">Personalizing your plan…</Badge>
        </p>
      ) : null}
    </div>
  );
}

function ResultsSkeleton() {
  return (
    <div className="mx-auto max-w-md space-y-6">
      <Skeleton className="h-9 w-40" />
      <div className="flex items-center gap-8">
        <Skeleton className="h-40 w-40 rounded-card" />
        <Skeleton className="h-44 w-44 rounded-full" />
      </div>
      <Skeleton className="h-64 w-full rounded-card" />
      <Skeleton className="h-12 w-full rounded-card" />
    </div>
  );
}

function InsightsSection({ insights, loading }: { insights?: Insights; loading: boolean }) {
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
            {percentile.percentile != null
              ? `You beat ${percentile.percentile}% of ${percentile.peer_count} peer${
                  percentile.peer_count === 1 ? "" : "s"
                }.`
              : "Analyze more photos to see your rank."}
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

function HarmonySection({ harmony, loading }: { harmony?: Harmony; loading: boolean }) {
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

      <div className="rounded-card gold-gradient p-5 text-black">
        <p className="text-xs font-semibold uppercase tracking-wide">{glow_up_card.headline}</p>
        <div className="mt-2 flex items-baseline gap-2">
          <span className="font-display text-4xl font-bold">{formatScore(glow_up_card.score)}</span>
          <span className="text-sm font-medium">{glow_up_card.label}</span>
        </div>
        <p className="mt-1 text-sm">
          {glow_up_card.archetype} · {glow_up_card.top_strength} · Day {glow_up_card.day}
        </p>
        <p className="mt-2 text-xs opacity-80">{glow_up_card.share_text}</p>
      </div>
    </div>
  );
}
