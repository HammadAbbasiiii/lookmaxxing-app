"use client";

import Link from "next/link";
import { Lock, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { tierLabel, type PaidTier } from "@/lib/tiers";

interface PaywallLockProps {
  title: string;
  teaser: string;
  description?: string;
  className?: string;
  /** Tier that unlocks this feature: "pro" (default) or "elite". */
  tier?: PaidTier;
  /**
   * Optional specifics to list inside the card. Lets a screen show one
   * consolidated ask instead of stacking several near-identical lock cards.
   */
  items?: readonly string[];
}

/**
 * A "locked premium perk" card: blurred teaser + upgrade CTA (§5.2 — UX only).
 * The real data lives behind `require_pro` on the backend; this card just makes
 * the *desire* visible without ever revealing the locked content.
 */
export function PaywallLock({
  title,
  teaser,
  description,
  className,
  tier = "pro",
  items,
}: PaywallLockProps) {
  const tierLabelText = tierLabel(tier);
  return (
    <div className={cn("relative overflow-hidden rounded-card card-border p-5", className)}>
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-display text-base font-semibold text-ink">{title}</h3>
        <span className="inline-flex shrink-0 items-center gap-1 rounded-full border border-gold/30 bg-gold/10 px-2 py-0.5 text-[11px] font-semibold text-gold-bright">
          <Lock className="h-3 w-3" aria-hidden /> {tierLabelText}
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

      {items?.length ? (
        <ul className="mt-3 space-y-1.5">
          {items.map((item) => (
            <li key={item} className="flex items-start gap-2 text-sm text-ink">
              <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gold" aria-hidden />
              {item}
            </li>
          ))}
        </ul>
      ) : null}

      {description ? <p className="mt-3 text-xs text-muted">{description}</p> : null}

      <Link href="/upgrade" className="mt-4 inline-block">
        <span className="gold-gradient inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-black">
          <Sparkles className="h-3.5 w-3.5" aria-hidden /> Upgrade to {tierLabelText}
        </span>
      </Link>
    </div>
  );
}
