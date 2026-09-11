"use client";

import { useEffect, useState } from "react";
import { Lock } from "lucide-react";

function msUntilNextUtcMidnight(): number {
  const now = new Date();
  const next = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() + 1),
  );
  return next.getTime() - now.getTime();
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/**
 * Locked "today's reveal" card. When a member has already opened today's
 * reveal, we keep them hooked for tomorrow with a live countdown (Zeigarnik
 * effect) plus a preview of what's coming.
 */
export function CountdownReveal() {
  const [ms, setMs] = useState<number>(() => msUntilNextUtcMidnight());

  useEffect(() => {
    const id = setInterval(() => setMs(msUntilNextUtcMidnight()), 1000);
    return () => clearInterval(id);
  }, []);

  const hours = Math.floor(ms / 3_600_000);
  const minutes = Math.floor((ms % 3_600_000) / 60_000);
  const seconds = Math.floor((ms % 60_000) / 1000);

  const dayMs = 24 * 3_600_000;
  const elapsed = Math.max(0, dayMs - ms);
  const pct = Math.min(100, Math.round((elapsed / dayMs) * 100));

  return (
    <div className="rounded-card card-border border-gold/30 p-5 text-center">
      <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-surface-2 text-gold">
        <Lock className="h-7 w-7" aria-hidden />
      </div>
      <h3 className="font-display text-lg font-semibold text-ink">🔒 Today&apos;s reveal</h3>
      <p className="mt-2 font-display text-3xl font-bold tabular-nums text-gold-bright">
        {pad(hours)}:{pad(minutes)}:{pad(seconds)}
      </p>
      <p className="mt-1 text-sm text-muted">unlocks tomorrow</p>

      <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-surface-2">
        <div
          className="h-full rounded-full bg-gradient-to-r from-gold to-gold-bright transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="mt-1 text-xs text-muted">{pct}% to your next reveal</p>

      <p className="mt-4 text-sm text-muted">
        <span className="text-gold-bright">Coming:</span> New insight on your jawline potential
      </p>
    </div>
  );
}
