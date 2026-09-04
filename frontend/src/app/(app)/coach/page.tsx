"use client";

import { useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { getCoach } from "@/lib/api/endpoints";
import { useMe } from "@/hooks/useMe";
import { ApiError } from "@/lib/api/client";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { PaywallLock } from "@/components/ui/PaywallLock";
import { Reveal } from "@/components/landing/Reveal";

export default function CoachPage() {
  const { data: user } = useMe();
  const isPro = Boolean(
    user && (user.subscription_tier === "pro" || user.subscription_tier === "elite"),
  );

  const q = useQuery({
    queryKey: ["coach"],
    queryFn: getCoach,
    enabled: isPro,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 403) return false;
      return failureCount < 1;
    },
  });

  if (!isPro) {
    return (
      <div className="mx-auto max-w-md">
        <ScreenHeader title="Your daily coach" subtitle="One personalized tip every day." />
        <PaywallLock
          title="Daily AI coach"
          teaser="Tomorrow's tip is ready — a two-minute action built around your score, skin type, and goals."
          description="Free users see the plan, but Pro members get a daily nudge from a coach that actually knows their weak areas."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md">
      <ScreenHeader title="Your daily coach" subtitle="One personalized tip every day." />

      {q.isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full rounded-card" />
          <Skeleton className="h-40 w-full rounded-card" />
        </div>
      ) : q.isError ? (
        <p className="rounded-card card-border p-6 text-sm text-muted">
          Couldn&apos;t load today&apos;s tip. Try again.
        </p>
      ) : (
        <Reveal>
          <Card className="border-gold/30">
            <div className="flex items-center gap-2 text-gold-bright">
              <Sparkles className="h-4 w-4" aria-hidden />
              <p className="text-xs font-semibold uppercase tracking-wide">
                {q.data?.focus ? `Today's focus · ${q.data.focus}` : "Today's tip"}
              </p>
            </div>
            <p className="mt-3 font-display text-lg font-semibold text-ink">{q.data?.message}</p>
            <ul className="mt-4 space-y-2">
              {(q.data?.tasks ?? []).map((t, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-muted">
                  <span className="mt-0.5 text-gold">✓</span> {t}
                </li>
              ))}
            </ul>
          </Card>
        </Reveal>
      )}

      <p className="mt-4 text-center text-xs text-muted">
        New tip every day. Come back tomorrow to keep the streak alive.
      </p>
    </div>
  );
}
