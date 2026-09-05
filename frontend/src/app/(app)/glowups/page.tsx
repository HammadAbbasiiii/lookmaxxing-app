"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Clapperboard, Eye, EyeOff, Flag, Lock, RefreshCw, Sparkles, Users } from "lucide-react";
import {
  getGlowupsFeed,
  setGlowupsConsent,
  getGlowupsConsent,
  getGlowupsMovie,
  generateGlowupsMovie,
  reportGlowupsItem,
} from "@/lib/api/endpoints";
import { useMe } from "@/hooks/useMe";
import type { GlowupFeedItem } from "@/lib/zod";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorCard } from "@/components/ui/ErrorCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { SafeImage } from "@/components/ui/SafeImage";
import { cn } from "@/lib/utils";

function FeedCard({ item, onReport }: { item: GlowupFeedItem; onReport: (id: string) => void }) {
  const [revealed, setRevealed] = useState(false);
  const blurPx = revealed ? 3 : 12;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="overflow-hidden rounded-card card-border"
    >
      <button
        type="button"
        onClick={() => setRevealed((v) => !v)}
        className="relative block h-56 w-full overflow-hidden bg-surface-2"
        aria-label={revealed ? "Hide transformation" : "Reveal transformation"}
      >
        {item.cover_url ? (
          <div style={{ filter: `blur(${blurPx}px)`, transform: "scale(1.08)" }} className="h-full w-full">
            <SafeImage src={item.cover_url} alt="Anonymized transformation" className="h-full w-full" />
          </div>
        ) : (
          <div className="flex h-full w-full items-center justify-center text-5xl">✨</div>
        )}
        <span className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 transition-opacity hover:opacity-100">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-black/60 px-3 py-1 text-xs font-medium text-white">
            {revealed ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            {revealed ? "Hide" : "Reveal"}
          </span>
        </span>
      </button>

      <div className="p-4">
        <div className="flex items-center justify-between gap-2">
          <p className="font-display text-base font-semibold text-ink">
            {item.first_name}{item.age ? `, ${item.age}` : ""}
          </p>
          {item.seed ? <Badge variant="outline">early tester</Badge> : <Badge variant="muted">member</Badge>}
        </div>
        <p className="mt-0.5 text-sm font-medium text-gold-bright">
          Day {item.day} · {item.delta >= 0 ? "+" : ""}{item.delta} pts
        </p>
        <p className="mt-1 text-sm text-muted">“{item.headline}”</p>

        {!item.seed ? (
          <button
            type="button"
            onClick={() => onReport(item.id)}
            className="mt-3 inline-flex items-center gap-1 text-xs text-muted transition-colors hover:text-danger"
          >
            <Flag className="h-3 w-3" /> Report
          </button>
        ) : null}
      </div>
    </motion.div>
  );
}


export default function GlowupsPage() {
  const qc = useQueryClient();
  const { data: me } = useMe();
  const tier = me?.subscription_tier ?? "free";
  const isElite = tier === "elite";
  const isAdult = me?.age != null && me.age >= 18;

  const feed = useQuery({
    queryKey: ["glowups-feed"],
    queryFn: () => getGlowupsFeed(0),
    staleTime: 30_000,
  });

  const movie = useQuery({
    queryKey: ["glowups-movie"],
    queryFn: getGlowupsMovie,
    enabled: isElite,
    retry: (count, error) => (error instanceof Error ? count < 1 : false),
  });

  const consentState = useQuery({
    queryKey: ["glowups-consent"],
    queryFn: getGlowupsConsent,
  });

  const consent = useMutation({
    mutationFn: setGlowupsConsent,
    onSuccess: (data) => {
      qc.setQueryData(["glowups-consent"], data);
      qc.invalidateQueries({ queryKey: ["glowups-feed"] });
    },
  });

  const generate = useMutation({
    mutationFn: generateGlowupsMovie,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["glowups-movie"] }),
  });

  const report = useMutation({
    mutationFn: reportGlowupsItem,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["glowups-feed"] }),
  });

  const consentOn = consentState.data?.share_enabled ?? false;

  return (
    <div className="mx-auto max-w-md">
      <ScreenHeader
        title="Glow-Ups"
        subtitle="Real members, real progress — and your own movie."
        back
        backHref="/dashboard"
      />

      <Card className="mb-6">
        <div className="flex items-center justify-between">
          <h2 className="flex items-center gap-2 font-display text-base font-semibold text-ink">
            <Clapperboard className="h-4 w-4 text-gold" /> Your movie
          </h2>
          {!isElite ? <Badge variant="outline"><Lock className="h-3 w-3" /> Elite</Badge> : null}
        </div>

        {!isElite ? (
          <p className="mt-2 text-sm text-muted">
            Elite compiles your photos into a before/after transformation movie with teaser trailers.
          </p>
        ) : movie.isLoading ? (
          <Skeleton className="mt-3 h-24 w-full" />
        ) : movie.data ? (
          <div className="mt-3">
            <p className="text-sm text-ink">
              Status: <span className="font-semibold capitalize">{movie.data.status}</span>
              {movie.data.delta ? (
                <span className="ml-1 text-gold-bright">· {movie.data.delta >= 0 ? "+" : ""}{movie.data.delta} pts</span>
              ) : null}
            </p>
            {movie.data.trailers.length > 0 ? (
              <p className="mt-1 text-xs text-muted">
                {movie.data.trailers.map((t) => t.title).join(" · ")}
              </p>
            ) : null}
            <Button
              className="mt-3"
              size="sm"
              variant="secondary"
              loading={generate.isPending}
              onClick={() => generate.mutate()}
            >
              <RefreshCw className="h-3.5 w-3.5" /> {movie.data.status === "ready" ? "Re-render" : "Generate movie"}
            </Button>
            {generate.data?.throttled ? (
              <p className="mt-2 text-xs text-muted">One render per day — your latest is ready.</p>
            ) : null}
          </div>
        ) : null}
      </Card>

      <Card className="mb-6">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-ink">Share my transformation</h2>
            <p className="mt-0.5 text-xs text-muted">Anonymized, first-name-only, always opt-in. Off by default.</p>
          </div>
          <button
            type="button"
            disabled={!isAdult || consent.isPending}
            onClick={() => consent.mutate(!consentOn)}
            className={cn(
              "relative h-7 w-12 shrink-0 rounded-full transition-colors disabled:opacity-40",
              consentOn ? "gold-gradient" : "bg-surface-2 ring-1 ring-border-soft",
            )}
            aria-pressed={consentOn}
            aria-label="Toggle share consent"
          >
            <span
              className={cn(
                "absolute top-1 h-5 w-5 rounded-full bg-ink transition-all",
                consentOn ? "left-6" : "left-1",
              )}
            />
          </button>
        </div>
        {!isAdult ? (
          <p className="mt-2 text-xs text-warning">The feed and sharing are for ages 18+.</p>
        ) : null}
      </Card>

      <section>
        <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
          <Users className="h-4 w-4 text-gold" /> Real transformations
        </h2>

        {feed.isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-64 w-full rounded-card" />
            <Skeleton className="h-64 w-full rounded-card" />
          </div>
        ) : feed.isError ? (
          <ErrorCard message="Couldn't load the feed. Try again." onRetry={() => feed.refetch()} />
        ) : feed.data?.locked ? (
          <EmptyState
            icon={<Lock className="h-8 w-8" />}
            title="18+ only"
            description="The transformation feed is hidden for members under 18 — your own solo movie is still yours."
          />
        ) : feed.data && feed.data.items.length > 0 ? (
          <div className="space-y-3">
            {feed.data.items.map((item) => (
              <FeedCard key={item.id} item={item} onReport={(id) => report.mutate(id)} />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Sparkles className="h-8 w-8" />}
            title="Be the first"
            description="No transformations shared yet. Opt in and be the first real proof."
          />
        )}
      </section>
    </div>
  );
}


