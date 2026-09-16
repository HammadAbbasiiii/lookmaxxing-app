"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Camera } from "lucide-react";
import { getAnalysisHarmony, getAnalysisInsights, getLatestPhoto } from "@/lib/api/endpoints";
import { useMe } from "@/hooks/useMe";
import { InsightsSection, HarmonySection } from "@/components/insights/InsightSections";
import { PaywallLock } from "@/components/ui/PaywallLock";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { ApiError } from "@/lib/api/client";
import { STALE } from "@/lib/constants";
import { Reveal } from "@/components/landing/Reveal";

/** Dedicated premium surface: latest analysis's Pro insights + Elite harmony. */
export default function GlowUpPage() {
  const { data: me } = useMe();
  const tier = me?.subscription_tier ?? "free";
  const isPro = tier === "pro" || tier === "elite";
  const isElite = tier === "elite";

  const latest = useQuery({
    queryKey: ["latest-photo"],
    queryFn: getLatestPhoto,
    staleTime: STALE.analysis,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) return false;
      return failureCount < 1;
    },
  });

  const photoId = latest.data?.id ?? "";

  const insights = useQuery({
    queryKey: ["insights", photoId],
    queryFn: () => getAnalysisInsights(photoId),
    enabled: isPro && Boolean(photoId),
    staleTime: STALE.analysis,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 403) return false;
      return failureCount < 1;
    },
  });

  const harmony = useQuery({
    queryKey: ["harmony", photoId],
    queryFn: () => getAnalysisHarmony(photoId),
    enabled: isElite && Boolean(photoId),
    staleTime: STALE.analysis,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 403) return false;
      return failureCount < 1;
    },
  });

  return (
    <div className="mx-auto max-w-md">
      <ScreenHeader
        title="Your Glow-Up"
        subtitle="Forecast · rank · archetype · harmony"
        back
        backHref="/dashboard"
      />

      {latest.isLoading ? (
        <Skeleton className="h-64 w-full rounded-card" />
      ) : latest.isError ? (
        <EmptyState
          icon={<Camera className="h-8 w-8" aria-hidden />}
          title="No analysis yet"
          description="Upload your first photo to unlock your Glow-Up forecast, percentile rank, archetype and harmony map."
          action={
            <Link href="/upload">
              <Button>Upload a photo</Button>
            </Link>
          }
        />
      ) : (
        <>
          {/* One ask instead of two stacked walls: a free user gets a single card
              that names both tiers' specifics, so the pitch is read once rather
              than twice in a row before any value is shown. */}
          {!isPro ? (
            <PaywallLock
              title="Unlock your Glow-Up insights"
              teaser="Glow-Up Forecast · Percentile rank · Look-alike archetype — all based on your face."
              description="Pro adds the projected Day-30/60/90 score, where you rank, and the archetype you project. Elite adds the golden-ratio harmony map and your 7-day blueprint."
              items={[
                "Your projected score at Day 30, 60 and 90",
                "Where you rank, and the archetype you project",
                "Elite also: golden-ratio harmony map + 7-day blueprint",
              ]}
            />
          ) : null}

          {isPro ? (
            <Reveal>
              <InsightsSection insights={insights.data} loading={insights.isLoading} />
            </Reveal>
          ) : null}

          {isElite ? (
            <Reveal delay={0.1}>
              <HarmonySection harmony={harmony.data} loading={harmony.isLoading} />
            </Reveal>
          ) : isPro ? (
            <PaywallLock
              className="mt-6"
              title="Elite harmony"
              teaser="Golden-ratio harmony map · 7-day glow-up blueprint · shareable score card."
              description="Elite measures your face against phi (1.618) and hands you a day-by-day blueprint plus a shareable card."
              tier="elite"
            />
          ) : null}
        </>
      )}
    </div>
  );
}
