"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ShoppingBag } from "lucide-react";
import { getAnalysis, getAnalysisHarmony, getAnalysisInsights, getPhotoStatus } from "@/lib/api/endpoints";
import { useMe } from "@/hooks/useMe";
import { GlowUpShareCard, HarmonySection, InsightsSection } from "@/components/insights/InsightSections";
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
import { isPaidTier, isEliteTier, normalizeTier } from "@/lib/tiers";

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
  const isFree = normalizeTier(tier) === "free";
  const isPro = isPaidTier(tier);
  const isElite = isEliteTier(tier);

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
  // Elite only — the shareable card ships with the harmony payload, so it
  // simply doesn't render for lower tiers (no fake preview).
  const card = harmony.data?.glow_up_card;
  const headroom = overall != null && potential != null ? potential - overall : null;
  const measurementUnavailable = a?.measurement?.landmarks === "unavailable";

  return (
    <div className="mx-auto max-w-md">
      {/* ── The reveal. This is the emotional peak of the whole product, so it
             gets the full width and a breathing glow. The motion comes from the
             ring's count-up plus `animate-pulse-glow` (an existing global
             utility) rather than framer-motion — importing that into this route
             cost +36 kB of First Load JS for a single entrance. ───────────── */}
      <ScreenHeader title="Your baseline" />

      <div className="glow-gold animate-pulse-glow card-border rounded-card px-5 py-8">
        <div className="flex flex-col items-center">
          <SafeImage src={a?.file_url} alt="Your photo" className="h-24 w-24 rounded-2xl" />

          <div className="mt-6">
            <ScoreRing score={overall} size={200} label={scoreLabel(overall ?? 0)} />
          </div>

          {potential != null ? (
            <p className="mt-6 text-center text-sm text-muted">
              Your potential is{" "}
              <span className="font-semibold text-gold-bright">~{formatScore(potential)}</span>
              {headroom != null && headroom > 0
                ? ` · ${formatScore(headroom)} points of headroom`
                : ""}
            </p>
          ) : null}

          {/* The Elite share card renders here, at the peak, instead of 80% down
              the page inside the harmony block. It carries its own share action,
              so the weaker "Share my score" button it replaces is gone. */}
          {card ? <GlowUpShareCard card={card} className="mt-6 w-full" /> : null}
        </div>
      </div>

      {/* ── What's working: free, specific and personal, delivered before we ask
             for anything. This used to sit *below* two paywalls. ──────────── */}
      {strengths.length ? (
        <div className="mt-6 rounded-card card-border p-5">
          <h2 className="text-sm font-semibold text-success">What&apos;s working</h2>
          <ul className="mt-2 space-y-1.5 text-sm text-muted">
            {strengths.slice(0, 4).map((item, i) => (
              <li key={i}>✓ {item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="mt-6 space-y-4 rounded-card card-border p-5">
        <h2 className="font-display text-lg font-semibold text-ink">Breakdown</h2>
        {CATEGORIES.map((c, i) => (
          <CategoryBar key={c.key} label={c.label} value={a?.scores?.[c.key]} delayMs={i * 60} />
        ))}
        {/* DEF-014: when the face couldn't be measured we say so once, in plain
            language, instead of leaving four rows that read like broken scores. */}
        {measurementUnavailable ? (
          <p className="text-xs text-muted">
            We couldn&apos;t read your facial landmarks, so these aren&apos;t measured yet.
            Upload a clear, front-facing photo in good light and we&apos;ll score them.
            {a?.measurement?.reason ? ` (${a.measurement.reason})` : ""}
          </p>
        ) : null}
      </div>

      {/* ── The ask: one card instead of two stacked walls, and it names the
             specifics rather than repeating "Unlock to reveal" twice. ─────── */}
      {isFree ? (
        <PaywallLock
          className="mt-6"
          title="Unlock your full report"
          teaser="Top 3 fixes · the exact routine · your projected Day 30/60/90 score."
          description="Your score, breakdown and strengths stay free. Pro adds the written plan for your weakest areas, plus the forecast, rank and archetype below."
          items={[
            "The written, coach-grade fix for each weak area",
            "Your projected score at Day 30, 60 and 90",
            "Where you rank, and the archetype you project",
          ]}
        />
      ) : null}

      {isPro ? <InsightsSection insights={insights.data} loading={insights.isLoading} /> : null}

      {isElite ? (
        <HarmonySection harmony={harmony.data} loading={harmony.isLoading} showCard={false} />
      ) : isPro ? (
        <PaywallLock
          className="mt-6"
          title="Elite harmony"
          teaser="Golden-ratio harmony map · 7-day glow-up blueprint · shareable score card."
          description="Elite measures your face against phi (1.618) and hands you a day-by-day blueprint plus a shareable card."
          tier="elite"
        />
      ) : null}

      <Link
        href="/peak-you"
        className="press lift mt-6 block rounded-card card-border p-5 hover:border-gold/40"
      >
        <div className="flex items-center justify-between gap-3">
          <div>
            <h3 className="font-display text-base font-semibold text-ink">Peak You</h3>
            <p className="mt-1 text-sm text-muted">
              Your peak score, day-by-day ascent and the person you&apos;re becoming.
            </p>
          </div>
          <ArrowRight className="h-5 w-5 shrink-0 text-gold" aria-hidden />
        </div>
      </Link>

      {/* ── Momentum: one clear next step, now ahead of any secondary detail. ── */}
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

      {/* "Room to grow" stays below the ask — the strengths version of this list
          now lives above the paywall, where it does its job. */}
      {weaknesses.length ? (
        <div className="mt-6 rounded-card card-border p-5">
          <h3 className="text-sm font-semibold text-warning">Room to grow</h3>
          <ul className="mt-2 space-y-1.5 text-sm text-muted">
            {weaknesses.slice(0, 4).map((item, i) => (
              <li key={i}>• {item}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {s && s.score == null && s.analysis_status !== "failed" ? (
        <p className="mt-4 text-center">
          <Badge variant="warning">Personalizing your plan…</Badge>
        </p>
      ) : null}

      {/* Honest framing, kept quiet so it never dampens the reveal above. */}
      <p className="mt-8 border-t border-border-soft pt-4 text-center text-xs leading-relaxed text-muted">
        Your score is an AI estimate from a single photo — not medical, dermatological or
        psychological advice. Lighting and camera angle affect the result, so compare
        like-for-like photos over time.
      </p>
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

