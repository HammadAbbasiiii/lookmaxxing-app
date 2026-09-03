"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ShoppingBag, Sparkles } from "lucide-react";
import { getAnalysis, getPhotoStatus } from "@/lib/api/endpoints";
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
