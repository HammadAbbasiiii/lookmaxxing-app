import { Lock } from "lucide-react";
import { cn } from "@/lib/utils";

interface LockChipProps {
  tier?: string;
  className?: string;
}

/** Small "Pro/Elite" lock chip — a UX hint only; the backend is the real gate. */
export function LockChip({ tier = "Pro", className }: LockChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-gold/30 bg-gold/10 px-2 py-0.5 text-[11px] font-semibold text-gold-bright",
        className,
      )}
    >
      <Lock className="h-3 w-3" aria-hidden />
      {tier}
    </span>
  );
}
