"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Flame, Gift, Sparkles } from "lucide-react";
import { getGlowState, openGlow, getGlowReveals } from "@/lib/api/endpoints";
import { useMe } from "@/hooks/useMe";
import type { GlowReveal } from "@/lib/zod";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorCard } from "@/components/ui/ErrorCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { SafeImage } from "@/components/ui/SafeImage";
import { cn, formatScore } from "@/lib/utils";

const RARITY_STYLE: Record<string, { ring: string; label: string }> = {
  common: { ring: "border-border-soft", label: "Common" },
  rare: { ring: "border-sky-400/50", label: "Rare" },
  epic: { ring: "border-purple-400/50", label: "Epic" },
  legendary: { ring: "border-gold/60", label: "Legendary" },
};

function RevealCard({ reveal, animate }: { reveal: GlowReveal; animate?: boolean }) {
  const payload = reveal.payload;
  const style = RARITY_STYLE[reveal.rarity] ?? RARITY_STYLE.common;
  const isGold = reveal.rarity === "legendary" || reveal.reward_type === "gold_glow";

  return (
    <motion.div
      initial={animate ? { opacity: 0, scale: 0.96 } : false}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className={cn("overflow-hidden rounded-card card-border border p-5", style.ring)}
    >
      <div className="flex items-center justify-between">
        <span className="text-4xl" aria-hidden>
          {payload.emoji || "🎁"}
        </span>
        <Badge variant={isGold ? "gold" : "muted"}>{style.label}</Badge>
      </div>

      <h3 className="mt-3 font-display text-xl font-semibold text-ink">{payload.headline}</h3>
      {payload.body ? <p className="mt-2 text-sm text-muted">{payload.body}</p> : null}

      {reveal.reward_type === "glimpse" || reveal.reward_type === "gold_glow" ? (
        <div className="relative mt-4 overflow-hidden rounded-xl bg-surface-2">
          <motion.div
            initial={animate ? { filter: `blur(${payload.blur_px ?? 24}px)` } : false}
            animate={{ filter: "blur(0px)" }}
            transition={{ duration: 1.4, ease: "easeOut", delay: 0.2 }}
          >
            <SafeImage src={payload.photo_url} alt="Your progress" className="h-64 w-full" />
          </motion.div>
        </div>
      ) : null}

      {reveal.reward_type === "full_reveal" ? (
        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-surface-2 p-2">
            <p className="mb-1 text-xs text-muted">Before</p>
            <SafeImage src={payload.before_url} alt="Before" className="h-40 w-full rounded-lg" />
            <p className="mt-1 text-center text-sm font-semibold text-ink">{formatScore(payload.before_score)}</p>
          </div>
          <div className="rounded-xl bg-surface-2 p-2">
            <p className="mb-1 text-xs text-muted">After</p>
            <SafeImage src={payload.after_url} alt="After" className="h-40 w-full rounded-lg" />
            <p className="mt-1 text-center text-sm font-semibold text-gold-bright">{formatScore(payload.after_score)}</p>
          </div>
        </div>
      ) : null}

      {payload.share_text ? (
        <p className="mt-3 text-xs text-muted">Share: “{payload.share_text}”</p>
      ) : null}
    </motion.div>
  );
}


export default function GlowPage() {
  const { data: me } = useMe();
  const tier = me?.subscription_tier ?? "free";
  const qc = useQueryClient();

  const state = useQuery({ queryKey: ["glow-state"], queryFn: getGlowState });
  const history = useQuery({ queryKey: ["glow-reveals"], queryFn: getGlowReveals });

  const open = useMutation({
    mutationFn: openGlow,
    onSuccess: (data) => {
      qc.setQueryData(["glow-state"], data);
      qc.invalidateQueries({ queryKey: ["glow-reveals"] });
    },
  });

  const [justOpened, setJustOpened] = useState(false);

  async function handleOpen() {
    setJustOpened(false);
    await open.mutateAsync();
    setJustOpened(true);
  }

  if (state.isLoading) {
    return (
      <div className="mx-auto max-w-md space-y-4">
        <Skeleton className="h-9 w-48" />
        <Skeleton className="h-64 w-full rounded-card" />
      </div>
    );
  }

  if (state.isError) {
    return (
      <div className="mx-auto max-w-md">
        <ScreenHeader title="Daily Glow" subtitle="Your future, one reveal at a time" back backHref="/dashboard" />
        <ErrorCard message="Couldn't load today's reveal. Try again." onRetry={() => state.refetch()} />
      </div>
    );
  }

  const s = state.data?.state;
  const reveal = state.data?.today_reveal ?? null;
  const canOpen = state.data?.can_open ?? false;

  return (
    <div className="mx-auto max-w-md">
      <ScreenHeader
        title="Daily Glow"
        subtitle={`Day ${s?.journey_day ?? 1}/90 · ${s?.glow_streak ?? 0}-day streak`}
        back
        backHref="/dashboard"
      />

      <div className="mb-5 flex items-center justify-between rounded-card card-border p-4">
        <div>
          <p className="text-xs text-muted">Today&apos;s blur</p>
          <p className="font-display text-2xl font-bold text-ink">{s?.blur_next ?? 24}px</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted">Sharpest at Day 90</p>
          <p className="inline-flex items-center gap-1 text-sm font-semibold text-gold-bright">
            <Flame className="h-4 w-4" /> {s?.longest_glow_streak ?? 0} best
          </p>
        </div>
      </div>

      {!reveal && canOpen ? (
        <Card className="text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-gold/15 text-gold">
            <Gift className="h-7 w-7" aria-hidden />
          </div>
          <h3 className="font-display text-lg font-semibold text-ink">Something real is waiting</h3>
          <p className="mt-1 text-sm text-muted">
            Open today&apos;s reveal — a genuine win, sharper every day you show up.
          </p>
          <Button className="mt-5" size="lg" loading={open.isPending} onClick={handleOpen}>
            <Sparkles className="h-4 w-4" /> Open today&apos;s reveal
          </Button>
        </Card>
      ) : null}

      {reveal ? (
        <RevealCard reveal={reveal} animate={justOpened} />
      ) : !canOpen ? (
        <EmptyState
          icon={<Gift className="h-8 w-8" />}
          title="Come back tomorrow"
          description="You've opened today's reveal. Keep your streak alive and tomorrow's will be sharper."
        />
      ) : null}

      {s?.full_reveal?.eligible ? (
        <div className="mt-5 rounded-card card-border border-gold/40 p-5">
          <h3 className="font-display text-base font-semibold text-ink">Day 90 full reveal</h3>
          <p className="mt-1 text-sm text-muted">
            {tier === "elite"
              ? "Your side-by-side before/after is ready at Day 90."
              : "Elite unlocks your full, zero-blur before/after at Day 90."}
          </p>
        </div>
      ) : null}

      {history.data && history.data.total > 0 ? (
        <div className="mt-6">
          <h3 className="mb-2 text-sm font-semibold text-ink">Your reveals</h3>
          <div className="space-y-2">
            {history.data.reveals.map((r) => (
              <div key={r.id} className="flex items-center gap-3 rounded-lg card-border p-3">
                <span className="text-xl">{r.payload.emoji || "🎁"}</span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-ink">{r.payload.headline}</p>
                  <p className="text-xs text-muted">Day {r.day} · {r.rarity}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

