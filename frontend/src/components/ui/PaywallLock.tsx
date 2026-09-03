"use client";

import Link from "next/link";
import { Lock, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface PaywallLockProps {
  title: string;
  teaser: string;
  description?: string;
  className?: string;
}

/**
 * A "locked premium perk" card: blurred teaser + upgrade CTA (§5.2 — UX only).
 * The real data lives behind `require_pro` on the backend; this card just makes
 * the *desire* visible without ever revealing the locked content.
 */
export function PaywallLock({ title, teaser, description, className }: PaywallLockProps) {
  return (
    <div className={cn("relative overflow-hidden rounded-card card-border p-5", className)}>
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-display text-base font-semibold text-ink">{title}</h3>
        <span className="inline-flex items-center gap-1 rounded-full border border-gold/30 bg-gold/10 px-2 py-0.5 text-[11px] font-semibold text-gold-bright">
          <Lock className="h-3 w-3" aria-hidden /> Pro
        </span>
      </div>

      {/* Blurred teaser — curiosity without revealing the real data. */}
      <div className="relative mt-3 select-none">
        <p className="text-sm text-muted blur-[6px]" aria-hidden>
          {teaser}
        </p>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-2 px-3 py-1 text-xs font-medium text-muted">
            <Sparkles className="h-3.5 w-3.5 text-gold" aria-hidden /> Unlock to reveal
          </span>
        </div>
      </div>

      {description ? <p className="mt-3 text-xs text-muted">{description}</p> : null}

      <Link href="/upgrade" className="mt-4 inline-block">
        <span className="gold-gradient inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-black">
          <Sparkles className="h-3.5 w-3.5" aria-hidden /> Upgrade to Pro
        </span>
      </Link>
    </div>
  );
}
