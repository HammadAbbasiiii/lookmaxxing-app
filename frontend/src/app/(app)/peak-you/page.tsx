"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Camera } from "lucide-react";
import { getAnalysis, getAnalysisInsights, getLatestPhoto } from "@/lib/api/endpoints";
import { useMe } from "@/hooks/useMe";
import { buildPeakYou, futureSelfMessage, journeyDay } from "@/lib/peak";
import { PeakYouReveal, TwoFutures, FutureSelfCard } from "@/components/peak/PeakYou";
import { PaywallLock } from "@/components/ui/PaywallLock";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { ApiError } from "@/lib/api/client";
import { STALE } from "@/lib/constants";

/** "Peak You" — meet the version of you that's already on the other side of 90 days. */
export default function PeakYouPage() {
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

  const analysis = useQuery({
    queryKey: ["analysis", photoId],
    queryFn: () => getAnalysis(photoId),
    enabled: Boolean(photoId),
    staleTime: STALE.analysis,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) return false;
      return failureCount < 1;
    },
  });

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

  const peak = buildPeakYou(analysis.data, insights.data);
  const message = peak ? futureSelfMessage(peak, journeyDay(peak)) : null;

  return (
    <div className="mx-auto max-w-md">
      <ScreenHeader
        title="Peak You"
        subtitle="Meet the version of you that's already on the other side."
        back
        backHref="/dashboard"
      />

      {latest.isLoading ? (
        <Skeleton className="h-64 w-full rounded-card" />
      ) : latest.isError ? (
        <EmptyState
          icon={<Camera className="h-8 w-8" aria-hidden />}
          title="No analysis yet"
          description="Upload your first photo to see the version of you that's 90 days away."
          action={
            <Link href="/upload">
              <Button>Upload a photo</Button>
            </Link>
          }
        />
      ) : !isPro ? (
        <>
          <TwoFutures currentScore={analysis.data?.scores?.overall ?? 0} />
          <PaywallLock
            className="mt-6"
            title="The full reveal"
            teaser="Your peak score · day-by-day ascent · your biggest lever · who you're becoming."
            description="Pro unlocks your projected peak and the exact path to it."
          />
        </>
      ) : (
        <>
          {peak ? (
            <PeakYouReveal peak={peak} />
          ) : insights.isLoading ? (
            <Skeleton className="h-64 w-full rounded-card" />
          ) : null}

          {isElite ? (
            message ? (
              <FutureSelfCard message={message} />
            ) : null
          ) : (
            <PaywallLock
              className="mt-6"
              title="Your future self"
              teaser="A daily message from the person you're becoming — keeps you on the path."
              description="Elite adds a daily check-in from your future self, so you never drift."
            />
          )}
        </>
      )}
    </div>
  );
}
