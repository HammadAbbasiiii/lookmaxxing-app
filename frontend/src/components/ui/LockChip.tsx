import { Lock } from "lucide-react";
import { cn } from "@/lib/utils";
import { tierLabel, type PaidTier } from "@/lib/tiers";

interface LockChipProps {
  /** Minimum tier that unlocks the thing this chip sits next to. */
  tier?: PaidTier;
  /** Hide the word and keep just the padlock (tight nav rows). */
  iconOnly?: boolean;
  /** Drop the pill background/border — for use inside nav tabs. */
  bare?: boolean;
  className?: string;
}

/**
 * Small "Pro/Elite" lock chip — a UX hint only; the backend is the real gate.
 * Used in the navs so a gated destination is obvious before it is tapped, and
 * inside cards/rows so a mixed list stays readable.
 *
 * `bare` swaps the pill styling out rather than overriding it: `cn()` is a plain
 * join, so a className override would leave both `border` and `border-none` in
 * the class list and let stylesheet order decide the winner.
 */
export function LockChip({
  tier = "pro",
  iconOnly = false,
  bare = false,
  className,
}: LockChipProps) {
  const label = tierLabel(tier);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-[11px] font-semibold text-gold-bright",
        bare ? "" : "rounded-full border border-gold/30 bg-gold/10 px-2 py-0.5",
        className,
      )}
    >
      <Lock className="h-3 w-3" aria-hidden />
      {iconOnly ? <span className="sr-only">{label}</span> : label}
    </span>
  );
}
