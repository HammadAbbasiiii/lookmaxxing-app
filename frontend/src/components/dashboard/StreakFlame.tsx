"use client";

import { cn } from "@/lib/utils";

type StreakVisual = {
  icon: string;
  size: "small" | "medium" | "large" | "xl";
  color: "gray" | "white" | "gold" | "rainbow";
  glow: boolean;
};

/**
 * The streak flame escalates with streak length, so the visual reward grows
 * the longer you keep the chain alive (streak < 7 → one flame, < 30 → two,
 * < 90 → three, 90+ → four with a glow).
 */
export function getStreakVisual(streak: number): StreakVisual {
  if (streak === 0) return { icon: "🔥", size: "small", color: "gray", glow: false };
  if (streak < 7) return { icon: "🔥", size: "small", color: "white", glow: false };
  if (streak < 30) return { icon: "🔥🔥", size: "medium", color: "gold", glow: false };
  if (streak < 90) return { icon: "🔥🔥🔥", size: "large", color: "gold", glow: true };
  return { icon: "🔥🔥🔥🔥", size: "xl", color: "rainbow", glow: true };
}

const SIZE_CLASS: Record<StreakVisual["size"], string> = {
  small: "text-base",
  medium: "text-xl",
  large: "text-2xl",
  xl: "text-3xl",
};

export function StreakFlame({ streak, className }: { streak: number; className?: string }) {
  const v = getStreakVisual(streak);

  return (
    <span
      className={cn(
        "leading-none",
        SIZE_CLASS[v.size],
        v.color === "gray" && "opacity-40 grayscale",
        v.color === "gold" && "drop-shadow-[0_0_8px_rgba(251,191,36,0.55)]",
        v.color === "rainbow" && "drop-shadow-[0_0_12px_rgba(251,191,36,0.85)] animate-pulse",
        className,
      )}
      aria-hidden
    >
      {v.icon}
    </span>
  );
}
