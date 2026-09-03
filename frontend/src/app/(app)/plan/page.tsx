"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Flame, UploadCloud } from "lucide-react";
import { toast } from "sonner";
import { getPlan, postPlanCheckin } from "@/lib/api/endpoints";
import { STALE } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card, CardTitle } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorCard } from "@/components/ui/ErrorCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { ApiError } from "@/lib/api/client";

export default function PlanPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["plan"], queryFn: getPlan, staleTime: STALE.plan });

  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const tasks = q.data?.this_week?.daily_tasks ?? [];

  useEffect(() => {
    if (q.data?.has_plan) setChecked({});
  }, [q.data?.has_plan, q.data?.current?.day]);

  const checkin = useMutation({
    mutationFn: (completed: string[]) => postPlanCheckin(completed),
    onSuccess: (result) => {
      toast.success(result.streak_message || "Check-in logged.");
      qc.invalidateQueries({ queryKey: ["plan"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["me"] });
    },
    onError: (e) => {
      if (e instanceof ApiError && e.status === 403) {
        toast.error("Upgrade to Pro to unlock daily check-ins.");
        router.push("/upgrade");
      } else if (e instanceof ApiError && e.status === 409) {
        toast.error("You've already checked in today. Come back tomorrow.");
        qc.invalidateQueries({ queryKey: ["plan"] });
      } else {
        toast.error(e instanceof ApiError ? e.message : "Couldn't check in. Try again.");
      }
    },
  });

  if (q.isLoading) return <PlanSkeleton />;
  if (q.isError) {
    return (
      <div className="mx-auto max-w-md pt-10">
        <ErrorCard message="Something went wrong. Please try again." onRetry={() => q.refetch()} />
      </div>
    );
  }

  const d = q.data;

  if (!d || !d.has_plan) {
    return (
      <div>
        <ScreenHeader title="Your plan" />
        <div className="mx-auto max-w-md">
          <EmptyState
            icon={<UploadCloud className="h-8 w-8" />}
            title="No active plan"
            description="Upload and analyze a photo to generate your personalised 90-day plan."
            action={
              <Link href="/upload">
                <Button size="lg">Analyze a photo</Button>
              </Link>
            }
          />
        </div>
      </div>
    );
  }

  function toggleTask(name: string) {
    setChecked((prev) => ({ ...prev, [name]: !prev[name] }));
  }

  function submitCheckin() {
    const completed = tasks.filter((t) => checked[t.name]).map((t) => t.name);
    checkin.mutate(completed);
  }

  const completedCount = tasks.filter((t) => checked[t.name]).length;
  const phase = d.phases?.[d.current.phase as keyof typeof d.phases];
  const alreadyDone = Boolean(d.checked_in_today);

  return (
    <div>
      <ScreenHeader
        title={`Day ${d.current.day}/${d.total_days}`}
        subtitle="Stay consistent to build lasting habits."
        action={
          <Badge variant="gold">
            <Flame className="h-3.5 w-3.5" /> {d.streak}-day streak
          </Badge>
        }
      />

      {/* Phase header */}
      <Card className="mb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted">Current phase</p>
            <p className="font-display text-lg font-semibold text-ink">
              {d.current.phase_title || "Building momentum"}
            </p>
            {d.current.phase_emotional_goal ? (
              <p className="mt-1 text-sm text-muted">{d.current.phase_emotional_goal}</p>
            ) : null}
          </div>
          <Badge variant="muted">{phase?.days || "90 days"}</Badge>
        </div>
        {/* Phase chips */}
        <div className="mt-4 grid grid-cols-3 gap-2 text-center">
          {(Object.values(d.phases ?? {}) as { title: string; complete: boolean }[]).map(
            (p, i) => (
              <div
                key={i}
                className={cn(
                  "rounded-lg px-2 py-2 text-xs font-medium",
                  p.complete ? "bg-success/10 text-success" : "bg-surface-2 text-muted",
                )}
              >
                {p.title || `Phase ${i + 1}`}
                {p.complete ? " ✓" : ""}
              </div>
            ),
          )}
        </div>
      </Card>

      {/* Today's tasks */}
      <Card>
        <CardTitle>Today&apos;s tasks</CardTitle>
        {tasks.length ? (
          <ul className="mt-3 space-y-2">
            {tasks.map((task) => {
              const done = Boolean(checked[task.name]);
              return (
                <li key={task.name}>
                  <button
                    type="button"
                    onClick={() => !alreadyDone && toggleTask(task.name)}
                    disabled={alreadyDone}
                    className={cn(
                      "flex w-full items-start gap-3 rounded-xl border p-3 text-left transition-colors",
                      done ? "border-success/30 bg-success/5" : "border-border-soft bg-surface-2 hover:border-gold/40",
                      alreadyDone && "cursor-not-allowed opacity-70",
                    )}
                    aria-pressed={done}
                  >
                    <span
                      className={cn(
                        "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md border",
                        done ? "border-success bg-success text-black" : "border-border-soft",
                      )}
                    >
                      {done ? <Check className="h-3.5 w-3.5" /> : null}
                    </span>
                    <span className="flex-1">
                      <span className={cn("block text-sm font-medium", done ? "text-muted line-through" : "text-ink")}>
                        {task.name}
                      </span>
                      {task.details ? (
                        <span className="mt-0.5 block text-xs text-muted">{task.details}</span>
                      ) : null}
                    </span>
                    {task.time ? <Badge variant="muted">{task.time}</Badge> : null}
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="mt-3 text-sm text-muted">No tasks for this week yet.</p>
        )}

        {alreadyDone ? (
          <div className="mt-4 rounded-xl border border-success/30 bg-success/5 p-3 text-center">
            <p className="text-sm font-medium text-success">✓ Done for today</p>
            <p className="mt-1 text-xs text-muted">Come back tomorrow to keep your streak alive.</p>
          </div>
        ) : (
          <Button
            onClick={submitCheckin}
            disabled={completedCount === 0}
            loading={checkin.isPending}
            fullWidth
            className="mt-4"
          >
            {completedCount > 0
              ? `Check in (${completedCount}/${tasks.length})`
              : "Check in today's tasks"}
          </Button>
        )}
      </Card>

      {/* Quote / bonus tip */}
      {d.todays_quote?.text ? (
        <Card className="mt-4">
          <p className="text-sm italic text-muted">“{d.todays_quote.text}”</p>
          {d.todays_quote.author ? (
            <p className="mt-1 text-xs text-muted">— {d.todays_quote.author}</p>
          ) : null}
        </Card>
      ) : d.bonus_tip ? (
        <Card className="mt-4">
          <p className="text-sm text-muted">
            <span className="font-semibold text-gold-bright">Tip: </span>
            {d.bonus_tip}
          </p>
        </Card>
      ) : null}

      {/* Next milestone */}
      {d.upcoming_milestone ? (
        <div className="mt-4 rounded-card card-border p-4 text-center">
          <p className="text-sm text-muted">
            Next milestone:{" "}
            <span className="font-semibold text-ink">Day {d.upcoming_milestone.day}</span>
            {d.upcoming_milestone.days_remaining > 0 ? (
              <span className="text-muted"> — {d.upcoming_milestone.days_remaining} days to go</span>
            ) : null}
          </p>
        </div>
      ) : null}
    </div>
  );
}

function PlanSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-9 w-40" />
      <Skeleton className="h-32 w-full rounded-card" />
      <Skeleton className="h-56 w-full rounded-card" />
    </div>
  );
}
