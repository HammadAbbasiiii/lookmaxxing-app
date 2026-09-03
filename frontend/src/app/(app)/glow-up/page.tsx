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
          {!isPro ? (
            <>
              <PaywallLock
                title="Glow-Up insights"
                teaser="Glow-Up Forecast · Percentile rank · Look-alike archetype — all based on your face."
                description="Pro unlocks your projected Day-30/60/90 score, where you rank, and the archetype you project."
              />
              <PaywallLock
                className="mt-6"
                title="Elite harmony"
                teaser="Golden-ratio harmony map · 7-day glow-up blueprint · shareable score card."
                description="Elite measures your face against phi (1.618) and hands you a day-by-day blueprint plus a shareable card."
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
        </>
      )}
    </div>
  );
}
