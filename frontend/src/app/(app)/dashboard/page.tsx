"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Camera, Check, Flame, ListChecks, Lock, ShoppingBag, Sparkles } from "lucide-react";
import { getDashboard } from "@/lib/api/endpoints";
import { useEntitlements } from "@/hooks/useEntitlements";
import { STALE, scoreLabel } from "@/lib/constants";
import { cn, firstName, formatScore } from "@/lib/utils";
import { Card, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorCard } from "@/components/ui/ErrorCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { ProgressRing } from "@/components/ui/ProgressRing";
import { ScreenHeader } from "@/components/ui/ScreenHeader";

const PHASE_LABEL: Record<string, string> = {
  phase_1: "Foundation",
  phase_2: "Building",
  phase_3: "Mastery",
};

const PHASES = [
  { key: "phase_1", label: "Foundation", range: "Days 1–30" },
  { key: "phase_2", label: "Building", range: "Days 31–60" },
  { key: "phase_3", label: "Mastery", range: "Days 61–90" },
];

const PHASE_ORDER = ["phase_1", "phase_2", "phase_3"];

/**
 * The live backend can return `next_action.task` as a stringified Python dict
 * (e.g. "{'task': 'Water rinse…', 'time': 'AM', 'duration_minutes': 1}") when a
 * plan task uses the `task` key instead of `name`. Extract the real title so the
 * "Next up" card never renders a raw object literal.
 */
function nextActionText(raw: unknown): string {
  if (raw == null) return "";
  if (typeof raw === "string") {
    const s = raw.trim();
    if (!s) return "";
    if (s.startsWith("{") && s.endsWith("}")) {
      const match = s.match(/['"]task['"]\s*:\s*['"]([^'"]*)['"]/);
      if (match && match[1]) return match[1];
    }
    return s;
  }
  if (typeof raw === "object") {
    const o = raw as Record<string, unknown>;
    const task = o.task ?? o.name ?? o.title;
    if (typeof task === "string" && task.trim()) return task.trim();
  }
  return "";
}

function StreakStrip({ streak, checkedToday }: { streak: number; checkedToday: boolean }) {
  const labels = [...Array(7)].map((_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return d.toLocaleDateString(undefined, { weekday: "narrow" });
  });

  return (
    <div className="flex items-center gap-1.5" aria-label={`${streak}-day streak`}>
      {labels.map((label, i) => {
        const isToday = i === 6;
        const filled = checkedToday
          ? i >= 7 - Math.min(streak, 7)
          : i >= 6 - Math.min(streak, 7) && i < 6;
        return (
          <div
            key={i}
            className={cn(
              "flex h-9 w-9 items-center justify-center rounded-full text-xs font-semibold",
              filled ? "bg-gold text-black" : "bg-surface-2 text-muted",
              isToday && !filled && "ring-2 ring-gold/60",
            )}
          >
            {filled ? <Check className="h-4 w-4" /> : label}
          </div>
        );
      })}
    </div>
  );
}

export default function DashboardPage() {
  const q = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
    staleTime: STALE.dashboard,
  });

  if (q.isLoading) return <DashboardSkeleton />;
  if (q.isError) {
    return (
      <div className="mx-auto max-w-md pt-10">
        <ErrorCard message="Something went wrong. Please try again." onRetry={() => q.refetch()} />
      </div>
    );
  }

  const d = q.data;
  if (!d) return null;
  const name = firstName(d.profile.full_name);
  const hasPhoto = d.plan?.has_plan === true || d.progress?.current_score != null;

  return (
    <div>
      <ScreenHeader
        title={name ? `Welcome back, ${name}.` : "Welcome back."}
        subtitle={hasPhoto ? "Here's where you stand today." : "Let's get your baseline."}
      />

      {!hasPhoto ? (
        <div className="mx-auto max-w-md">
          <EmptyState
            icon={<Camera className="h-8 w-8" />}
            title="Upload your first photo"
            description="Get your baseline score and a personalised 90-day plan."
            action={
              <Link href="/upload">
                <Button size="lg">Upload your first photo</Button>
              </Link>
            }
          />
        </div>
      ) : (
        <>
          <Card className="mb-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-full bg-gold/15 text-gold">
                  <Flame className="h-6 w-6" />
                </span>
                <div>
                  <p className="font-display text-xl font-bold text-ink">
                    {(d?.progress?.current_streak ?? 0) > 0
                      ? `${d?.progress?.current_streak ?? 0}-day streak`
                      : "Start your streak"}
                  </p>
                  <p className="text-xs text-muted">
                    {(d?.progress?.current_streak ?? 0) > 0
                      ? "Don't break the chain — check in daily."
                      : "Complete today's tasks to light the first flame."}
                    {d?.progress?.total_checkins ? ` · ${d.progress.total_checkins} check-ins` : ""}
                  </p>
                </div>
              </div>
              <StreakStrip
                streak={d?.progress?.current_streak ?? 0}
                checkedToday={Boolean(d?.progress?.checked_in_today)}
              />
            </div>
          </Card>

          <Card className="mb-4">
            <CardTitle>Your journey</CardTitle>
            <div className="mt-4 grid grid-cols-3 gap-2">
              {PHASES.map((p, i) => {
                const currentIdx = PHASE_ORDER.indexOf(d?.plan?.current_phase ?? "");
                const state =
                  currentIdx === -1 ? "upcoming" : i < currentIdx ? "done" : i === currentIdx ? "current" : "upcoming";
                return (
                  <div
                    key={p.key}
                    className={cn(
                      "rounded-xl border p-3 text-center",
                      state === "done"
                        ? "border-success/30 bg-success/5"
                        : state === "current"
                          ? "border-gold/40 bg-gold/5"
                          : "border-border-soft bg-surface-2",
                    )}
                  >
                    <p
                      className={cn(
                        "text-xs font-medium",
                        state === "done" ? "text-success" : state === "current" ? "text-gold-bright" : "text-muted",
                      )}
                    >
                      {state === "done" ? "✓ " : ""}
                      {p.label}
                    </p>
                    <p className="mt-0.5 text-[11px] text-muted">{p.range}</p>
                  </div>
                );
              })}
            </div>
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
          <Card className="flex flex-col items-center justify-center py-8">
            <ScoreRing
              score={d?.progress?.current_score}
              size={150}
              label={scoreLabel(d?.progress?.current_score ?? 0)}
            />
            {d?.progress?.improvement != null && d.progress.improvement > 0 ? (
              <Badge variant="success" className="mt-4">
                Up {formatScore(d.progress.improvement)} pts since Day 1
              </Badge>
            ) : null}
          </Card>

          <Card className="flex flex-col gap-4">
            <CardTitle>Your plan</CardTitle>
            <div className="flex items-center gap-4">
              <ProgressRing value={d?.plan?.progress_percentage ?? 0} size={84}>
                <span className="tabular text-sm font-semibold text-ink">
                  {Math.round(d?.plan?.progress_percentage ?? 0)}%
                </span>
              </ProgressRing>
              <div>
                <p className="text-sm text-muted">
                  Day {d?.plan?.current_day ?? 0}/{d?.plan?.total_days ?? 90}
                </p>
                <p className="mt-0.5 font-display text-lg font-semibold text-ink">
                  {PHASE_LABEL[d?.plan?.current_phase ?? ""] || d?.plan?.phase || "Getting started"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-xl bg-surface-2 p-3">
              <Flame className="h-5 w-5 text-gold" aria-hidden />
              <span className="text-sm text-ink">
                <strong className="tabular">{d?.progress?.current_streak ?? 0}</strong>-day streak
                <span className="text-muted"> · longest {d?.progress?.longest_streak ?? 0}</span>
              </span>
            </div>
            <div>
              <div className="mb-1 flex items-center justify-between text-xs text-muted">
                <span>{Math.round(d?.plan?.progress_percentage ?? 0)}% complete</span>
                <span>{d?.plan?.days_remaining ?? 0} days left</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-surface-2">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-gold to-gold-bright transition-all"
                  style={{ width: `${Math.min(100, Math.max(0, d?.plan?.progress_percentage ?? 0))}%` }}
                />
              </div>
            </div>
          </Card>

          <Card>
            <CardTitle>Next up</CardTitle>
            <div className="mt-3">
              <Badge variant="gold">{d?.next_action?.time || "Today"}</Badge>
              <p className="mt-2 font-display text-lg font-semibold text-ink">
                {nextActionText(d?.next_action?.task) || "Complete today's daily tasks"}
              </p>
              {d?.next_action?.description ? (
                <p className="mt-1 text-sm text-muted">{d.next_action.description}</p>
              ) : null}
            </div>
            <Link href="/plan" className="mt-4 inline-block">
              <Button variant="secondary" size="sm">
                View plan <ArrowUpRight className="h-4 w-4" />
              </Button>
            </Link>
          </Card>

          <Card>
            <CardTitle>Next milestone</CardTitle>
            {d.milestones.next ? (
              <div className="mt-3">
                <p className="font-display text-lg font-semibold text-ink">
                  {d.milestones.next.label}
                </p>
                <p className="mt-1 text-sm text-muted">
                  Day {d.milestones.next.day} · {d.milestones.next.days_until} day
                  {d.milestones.next.days_until === 1 ? "" : "s"} to go
                </p>
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted">You're all caught up. 🎉</p>
            )}
            <Link href="/progress" className="mt-4 inline-block">
              <Button variant="secondary" size="sm">
                View progress <ArrowUpRight className="h-4 w-4" />
              </Button>
            </Link>
          </Card>
        </div>
        </>
      )}

      <ProPerks />

      {/* Quick links */}
      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        {[
          { href: "/upload", label: "Upload new photo", sub: "Track a new check-in", icon: Camera },
          { href: "/plan", label: "View plan", sub: "Today's 2-minute tasks", icon: ListChecks },
          { href: "/glow-up", label: "Your Glow-Up", sub: "Forecast, rank & harmony", icon: Sparkles },
          { href: "/products", label: "Shop products", sub: "Matched to your goals", icon: ShoppingBag },
        ].map(({ href, label, sub, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className="group card-border rounded-card p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04),0_12px_32px_-16px_rgba(0,0,0,0.7)] transition-all hover:-translate-y-0.5 hover:border-gold/40"
          >
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-gold/15 text-gold transition-colors group-hover:bg-gold/25">
              <Icon className="h-5 w-5" aria-hidden />
            </span>
            <p className="mt-3 font-medium text-ink">{label}</p>
            <p className="text-xs text-muted">{sub}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}

function ProPerks() {
  const ent = useEntitlements();
  const perks = ent.data?.features?.filter((f) => f.locked).slice(0, 3) ?? [];

  if (!ent.data || perks.length === 0) return null;

  return (
    <div className="mt-6 rounded-card card-border p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 font-display text-base font-semibold text-ink">
          <Sparkles className="h-4 w-4 text-gold" aria-hidden /> Unlock the full picture
        </h2>
        <Link href="/upgrade">
          <Badge variant="gold" className="cursor-pointer hover:opacity-90">Upgrade</Badge>
        </Link>
      </div>
      <ul className="mt-3 space-y-2">
        {perks.map((p) => (
          <li key={p.key} className="flex items-start gap-2 text-sm text-muted">
            <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gold" aria-hidden />
            <span>
              <span className="font-medium text-ink">{p.name}</span> — {p.teaser}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-9 w-64" />
      <Skeleton className="h-5 w-40" />
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
        <Skeleton className="h-44" />
        <Skeleton className="h-44" />
      </div>
    </div>
  );
}
