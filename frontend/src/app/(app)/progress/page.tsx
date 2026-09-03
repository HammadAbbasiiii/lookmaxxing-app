"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Camera, TrendingUp } from "lucide-react";
import { getCompare, getMilestones, getProgress } from "@/lib/api/endpoints";
import { STALE } from "@/lib/constants";
import { formatScore, shortDate } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorCard } from "@/components/ui/ErrorCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { SafeImage } from "@/components/ui/SafeImage";
import { ScoreChart } from "@/components/ui/ScoreChart";
import { ScreenHeader } from "@/components/ui/ScreenHeader";

function trendCopy(trend: string | null | undefined, change: number | null | undefined): string {
  if (trend === "improving") return `You're up ${change != null && change > 0 ? "+" + formatScore(change) : ""} pts since Day 1. That's real.`;
  if (trend === "stable") return "Holding steady — the next photo will show the work.";
  if (trend === "declining") return "Progress isn't linear. Keep the streak alive.";
  return "Track your change with regular progress photos.";
}

export default function ProgressPage() {
  const progress = useQuery({ queryKey: ["progress"], queryFn: getProgress, staleTime: STALE.analysis });
  const compare = useQuery({ queryKey: ["compare"], queryFn: getCompare, staleTime: STALE.analysis });
  const milestones = useQuery({ queryKey: ["milestones"], queryFn: getMilestones, staleTime: STALE.analysis });

  if (progress.isLoading) return <ProgressSkeleton />;
  if (progress.isError) {
    return (
      <div className="mx-auto max-w-md pt-10">
        <ErrorCard message="Something went wrong. Please try again." onRetry={() => progress.refetch()} />
      </div>
    );
  }

  const photos = progress.data?.photos ?? [];
  const summary = progress.data?.progress;

  if (photos.length === 0) {
    return (
      <div>
        <ScreenHeader title="Progress" />
        <div className="mx-auto max-w-md">
          <EmptyState
            icon={<Camera className="h-8 w-8" />}
            title="No photos yet"
            description="Upload and analyze your first photo to start tracking your change."
            action={
              <Link href="/upload">
                <Button size="lg">Upload a photo</Button>
              </Link>
            }
          />
        </div>
      </div>
    );
  }

  const compareData = compare.data;
  const milestoneData = milestones.data;
  const baseline = compareData?.baseline;
  const latest = compareData?.latest;
  const nextMs = milestoneData?.next ?? null;
  const completedMs = milestoneData?.completed ?? [];

  const chartPoints = photos.map((p) => ({
    label: shortDate(p.date),
    value: p.score,
  }));

  return (
    <div>
      <ScreenHeader
        title="Progress"
        subtitle={trendCopy(summary?.trend, summary?.score_change)}
        action={
          <Link href="/upload">
            <Button size="sm">
              <Camera className="h-4 w-4" /> Upload photo
            </Button>
          </Link>
        }
      />

      {/* Summary */}
      <div className="mb-4 grid grid-cols-3 gap-3">
        <Card className="p-4 text-center">
          <p className="text-xs text-muted">Baseline</p>
          <p className="tabular mt-1 font-display text-2xl font-bold text-ink">
            {formatScore(summary?.baseline_score)}
          </p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-xs text-muted">Current</p>
          <p className="tabular mt-1 font-display text-2xl font-bold text-gold">
            {formatScore(summary?.current_score)}
          </p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-xs text-muted">Change</p>
          <p
            className={
              "tabular mt-1 font-display text-2xl font-bold " +
              ((summary?.score_change ?? 0) > 0 ? "text-success" : (summary?.score_change ?? 0) < 0 ? "text-warning" : "text-ink")
            }
          >
            {(summary?.score_change ?? 0) > 0 ? "+" : ""}
            {formatScore(summary?.score_change)}
          </p>
        </Card>
      </div>

      {/* Score chart */}
      <Card className="mb-4">
        <CardTitle>Score over time</CardTitle>
        <div className="mt-3">
          <ScoreChart points={chartPoints} />
        </div>
      </Card>

      {/* Before / after slider */}
      {baseline && latest && baseline.file_url && latest.file_url ? (
        <Card className="mb-4">
          <CardTitle>Before &amp; after</CardTitle>
          <BeforeAfterSlider
            before={baseline.file_url}
            after={latest.file_url}
            beforeScore={baseline.score}
            afterScore={latest.score}
          />
        </Card>
      ) : (
        <Card className="mb-4">
          <CardTitle>Before &amp; after</CardTitle>
          <p className="mt-3 text-sm text-muted">
            Take your next progress photo to see a side-by-side comparison.
          </p>
        </Card>
      )}

      {/* Milestones */}
      <Card>
        <CardTitle>Milestones</CardTitle>
        {nextMs ? (
          <div className="mt-3 flex items-center gap-2">
            <span className="text-xl">{nextMs.emoji || "🎯"}</span>
            <div>
              <p className="text-sm font-medium text-ink">{nextMs.title}</p>
              <p className="text-xs text-muted">
                Day {nextMs.day} · {nextMs.days_remaining} days away
              </p>
            </div>
          </div>
        ) : null}
        {completedMs.length ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {completedMs.map((m) => (
              <Badge key={m.day} variant="success">
                {m.emoji} Day {m.day} · {m.title}
              </Badge>
            ))}
          </div>
        ) : null}
        {!nextMs && !completedMs.length ? (
          <p className="mt-3 text-sm text-muted">Milestones unlock as your plan progresses.</p>
        ) : null}
      </Card>
    </div>
  );
}

function BeforeAfterSlider({
  before,
  after,
  beforeScore,
  afterScore,
}: {
  before: string;
  after: string;
  beforeScore: number | null;
  afterScore: number | null;
}) {
  const [pos, setPos] = useState(50);

  return (
    <div className="relative mt-3 aspect-[3/4] w-full select-none overflow-hidden rounded-xl">
      <SafeImage src={before} alt="Before" className="absolute inset-0 h-full w-full" />
      <div className="absolute inset-0" style={{ clipPath: `inset(0 0 0 ${pos}%)` }}>
        <SafeImage src={after} alt="After" className="h-full w-full" />
      </div>
      <div className="pointer-events-none absolute inset-y-0 w-0.5 bg-gold" style={{ left: `${pos}%` }} />
      <input
        type="range"
        min={0}
        max={100}
        value={pos}
        onChange={(e) => setPos(Number(e.target.value))}
        className="absolute inset-0 h-full w-full cursor-ew-resize opacity-0"
        aria-label="Drag to compare before and after"
      />
      <span className="pointer-events-none absolute left-3 top-3 rounded-full bg-black/70 px-2 py-0.5 text-xs text-ink">
        Before {formatScore(beforeScore)}
      </span>
      <span className="pointer-events-none absolute right-3 top-3 rounded-full bg-gold/90 px-2 py-0.5 text-xs font-semibold text-black">
        After {formatScore(afterScore)}
      </span>
    </div>
  );
}

function ProgressSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-9 w-40" />
      <Skeleton className="h-32 w-full rounded-card" />
      <Skeleton className="h-48 w-full rounded-card" />
      <Skeleton className="h-64 w-full rounded-card" />
    </div>
  );
}
