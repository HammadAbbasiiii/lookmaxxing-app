"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { Check, Crown, Lock, Sparkles, Swords, Trophy, Zap } from "lucide-react";
import { getArcState, claimArcQuest } from "@/lib/api/endpoints";
import type { ArcState } from "@/lib/zod";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ErrorCard } from "@/components/ui/ErrorCard";
import { Skeleton } from "@/components/ui/Skeleton";
import { ProgressRing } from "@/components/ui/ProgressRing";
import { cn } from "@/lib/utils";

function QuestRow({
  id,
  focus,
  task,
  why,
  xp,
  claimed,
  locked,
  onClaim,
  busy,
}: {
  id: string;
  focus: string;
  task: string;
  why: string;
  xp: number;
  claimed: boolean;
  locked: boolean;
  onClaim: (id: string) => void;
  busy: boolean;
}) {
  return (
    <div className="rounded-lg card-border p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-gold-bright">{focus}</p>
          <p className="mt-0.5 text-sm font-medium text-ink">{task}</p>
          <p className="mt-0.5 text-xs text-muted">{why}</p>
        </div>
        <div className="shrink-0 text-right">
          <Badge variant="gold" className="mb-2">+{xp} XP</Badge>
          {locked ? (
            <span className="inline-flex items-center gap-1 text-xs text-muted">
              <Lock className="h-3.5 w-3.5" /> Pro
            </span>
          ) : claimed ? (
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-success">
              <Check className="h-3.5 w-3.5" /> Claimed
            </span>
          ) : (
            <Button size="sm" variant="secondary" disabled={busy} onClick={() => onClaim(id)}>
              Claim
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function LevelUpBanner({ title }: { title: string | null }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -12, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="mb-4 flex items-center gap-3 rounded-card border border-gold/50 bg-gold/10 p-4"
    >
      <span className="flex h-10 w-10 items-center justify-center rounded-full gold-gradient text-black">
        <Trophy className="h-5 w-5" aria-hidden />
      </span>
      <div>
        <p className="font-display text-base font-semibold text-ink">Level up!</p>
        {title ? <p className="text-sm text-gold-bright">{title}</p> : null}
      </div>
    </motion.div>
  );
}


export default function ArcPage() {
  const qc = useQueryClient();
  const state = useQuery({ queryKey: ["arc-state"], queryFn: getArcState });
  const [levelUpTitle, setLevelUpTitle] = useState<string | null>(null);

  const claim = useMutation({
    mutationFn: claimArcQuest,
    onSuccess: (data) => {
      if (data.leveled_up) {
        setLevelUpTitle(data.new_title);
        setTimeout(() => setLevelUpTitle(null), 2600);
      }
      qc.invalidateQueries({ queryKey: ["arc-state"] });
      qc.invalidateQueries({ queryKey: ["arc-badges"] });
    },
  });

  if (state.isLoading) {
    return (
      <div className="mx-auto max-w-md space-y-4">
        <Skeleton className="h-9 w-48" />
        <Skeleton className="h-56 w-full rounded-card" />
        <Skeleton className="h-40 w-full rounded-card" />
      </div>
    );
  }

  if (state.isError) {
    return (
      <div className="mx-auto max-w-md">
        <ScreenHeader title="The Arc" subtitle="Your journey as a game worth winning" back backHref="/dashboard" />
        <ErrorCard message="Couldn't load your journey. Try again." onRetry={() => state.refetch()} />
      </div>
    );
  }

  const a: ArcState = state.data ?? {
    level: 1, total_xp: 0, xp_to_next: 100, title: "", archetype: "Rookie",
    milestone_title: null, premium: false, today_quests: [], badges: [], skill_tree: [],
  };

  const unlockedBadges = a.badges;
  const progressPct = a.xp_to_next > 0
    ? Math.round(((a.total_xp % 100) / ((a.total_xp % 100) + a.xp_to_next)) * 100)
    : 100;

  return (
    <div className="mx-auto max-w-md">
      <ScreenHeader
        title="The Arc"
        subtitle="Every real action earns XP — level up who you become."
        back
        backHref="/dashboard"
        action={
          a.milestone_title ? (
            <Badge variant="gold" className="shrink-0">
              <Crown className="h-3 w-3" /> {a.milestone_title}
            </Badge>
          ) : undefined
        }
      />

      <AnimatePresence>{levelUpTitle ? <LevelUpBanner title={levelUpTitle} /> : null}</AnimatePresence>

      <Card className="relative overflow-hidden">
        <div className="flex items-center gap-5">
          <ProgressRing value={progressPct} size={104} stroke={8}>
            <div className="text-center">
              <p className="font-display text-2xl font-bold text-ink">{a.level}</p>
              <p className="text-[10px] uppercase tracking-wide text-muted">Level</p>
            </div>
          </ProgressRing>
          <div className="min-w-0">
            <p className="truncate font-display text-lg font-semibold text-ink">{a.title || "The Rookie, Level 1"}</p>
            <p className="text-sm text-muted">{a.archetype}</p>
            <p className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-gold-bright">
              <Zap className="h-4 w-4" /> {a.xp_to_next} XP to Level {a.level + 1}
            </p>
            <p className="mt-0.5 text-xs text-muted">{a.total_xp} XP total</p>
          </div>
        </div>
      </Card>

      <section className="mt-6">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-ink">
            <Swords className="h-4 w-4 text-gold" /> Today&apos;s quests
          </h2>
          {!a.premium ? <Badge variant="outline"><Lock className="h-3 w-3" /> Pro</Badge> : null}
        </div>

        {a.today_quests.length === 0 ? (
          <Card className="text-center text-sm text-muted">Quests refresh tomorrow — keep your streak alive.</Card>
        ) : (
          <div className="space-y-2">
            {a.today_quests.map((q) => (
              <QuestRow
                key={q.id}
                id={q.id}
                focus={q.focus}
                task={q.task}
                why={q.why}
                xp={q.xp}
                claimed={q.claimed}
                locked={q.locked}
                busy={claim.isPending}
                onClaim={(id) => claim.mutate(id)}
              />
            ))}
          </div>
        )}
      </section>

      <section className="mt-6">
        <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
          <Sparkles className="h-4 w-4 text-gold" /> Skill tree
        </h2>
        <div className="grid grid-cols-3 gap-2">
          {a.skill_tree.map((node) => (
            <div
              key={node.key}
              className={cn(
                "flex flex-col items-center rounded-lg card-border p-3 text-center",
                node.unlocked ? "border-gold/40 bg-gold/5" : "opacity-60",
              )}
            >
              <span className="text-xl" aria-hidden>{node.emoji}</span>
              <p className="mt-1 text-xs font-medium text-ink">{node.name}</p>
              {node.unlocked ? <Check className="mt-1 h-3.5 w-3.5 text-gold" aria-hidden /> : null}
            </div>
          ))}
        </div>
      </section>

      <section className="mt-6">
        <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
          <Trophy className="h-4 w-4 text-gold" /> Badges
        </h2>
        {unlockedBadges.length === 0 ? (
          <Card className="text-center text-sm text-muted">No badges yet — complete a quest to earn your first.</Card>
        ) : (
          <div className="grid grid-cols-2 gap-2">
            {unlockedBadges.map((b) => (
              <div key={b.badge_key} className="flex items-center gap-2 rounded-lg card-border p-3">
                <span className="text-2xl" aria-hidden>{b.emoji}</span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-ink">{b.name}</p>
                  <p className="truncate text-xs text-muted">{b.description}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}


