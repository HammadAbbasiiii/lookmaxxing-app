"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, TrendingUp } from "lucide-react";
import { getExplore } from "@/lib/api/endpoints";
import { STALE } from "@/lib/constants";
import { formatScore } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { Card, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorCard } from "@/components/ui/ErrorCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import type { Transformation } from "@/lib/zod";

export default function ExplorePage() {
  const q = useQuery({ queryKey: ["explore"], queryFn: getExplore, staleTime: STALE.explore });

  if (q.isLoading) return <ExploreSkeleton />;
  if (q.isError) {
    return (
      <div className="mx-auto max-w-md pt-10">
        <ErrorCard message="Something went wrong. Please try again." onRetry={() => q.refetch()} />
      </div>
    );
  }

  const data = q.data;
  const transformations = data?.transformations ?? [];
  const articles = data?.articles ?? [];

  return (
    <div>
      <ScreenHeader
        title="Explore"
        subtitle="Real members. Real progress."
      />

      {/* Transformations — anonymized, no raw face URLs rendered (§5.11) */}
      <h2 className="font-display text-lg font-semibold text-ink">Transformations</h2>
      <p className="mb-3 mt-1 text-sm text-muted">
        Face-score gains from real members on their 90-day plans.
      </p>
      {transformations.length ? (
        <div className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {transformations.map((t) => (
            <TransformationCard key={t.id} t={t} />
          ))}
        </div>
      ) : (
        <div className="mb-8">
          <EmptyState
            icon={<TrendingUp className="h-8 w-8" />}
            title="Transformations coming soon"
            description="As members progress, anonymized before/after scores will appear here."
          />
        </div>
      )}

      {/* Articles */}
      <h2 className="mb-3 font-display text-lg font-semibold text-ink">Learn</h2>
      {articles.length ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {articles.map((a) => (
            <a
              key={a.id}
              href={a.url}
              target="_blank"
              rel="noopener noreferrer"
              className="card-border rounded-card p-5 transition-colors hover:border-gold/40"
            >
              <div className="flex items-start justify-between gap-3">
                <h3 className="font-medium text-ink">{a.title}</h3>
                <ArrowUpRight className="h-4 w-4 shrink-0 text-muted" aria-hidden />
              </div>
              <p className="mt-2 text-sm text-muted">{a.summary}</p>
            </a>
          ))}
        </div>
      ) : (
        <EmptyState title="Articles coming soon" description="Educational content is on the way." />
      )}
    </div>
  );
}

function TransformationCard({ t }: { t: Transformation }) {
  const delta = t.after_score - t.before_score;
  return (
    <div className="card-border rounded-card p-5">
      <div className="flex items-center justify-between">
        <p className="font-medium text-ink">{t.username}</p>
        <Badge variant="success">+{formatScore(delta)} pts</Badge>
      </div>
      <div className="mt-4 flex items-center justify-center gap-4">
        <div className="text-center">
          <p className="text-xs text-muted">Before</p>
          <p className="tabular font-display text-2xl font-bold text-muted">
            {Math.round(t.before_score)}
          </p>
        </div>
        <ArrowUpRight className="h-5 w-5 text-gold" aria-hidden />
        <div className="text-center">
          <p className="text-xs text-muted">After</p>
          <p className="tabular font-display text-2xl font-bold text-gold">
            {Math.round(t.after_score)}
          </p>
        </div>
      </div>
      <p className="mt-3 text-center text-xs text-muted">
        Score up {formatScore(delta)} points
      </p>
    </div>
  );
}

function ExploreSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-9 w-40" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
    </div>
  );
}
