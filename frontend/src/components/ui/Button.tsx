"use client";

import type { ButtonHTMLAttributes, PointerEvent } from "react";
import { Loader2 } from "lucide-react";
import { haptics } from "@/lib/haptics";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: "gold-gradient text-black font-semibold hover:opacity-90",
  secondary: "border border-border-soft bg-surface text-ink hover:bg-surface-2",
  ghost: "text-muted hover:text-ink hover:bg-surface",
  danger: "bg-danger/10 text-danger border border-danger/30 hover:bg-danger/20",
};

const SIZE_CLASSES: Record<Size, string> = {
  // `sm` is a deliberate compact exception for dense inline actions; the
  // default `md` and `lg` meet the 50px minimum tap target.
  sm: "h-9 px-3 text-sm rounded-lg",
  md: "h-[50px] px-5 text-sm rounded-xl",
  lg: "h-[52px] px-7 text-base rounded-full",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  fullWidth?: boolean;
  /**
   * Contact haptic on press-down. Defaults on for `primary` (the money/success
   * path) and off elsewhere — buzzing every ghost link is noise, and a signal
   * that fires on everything stops meaning anything. Android only, and gated
   * on the user having touched the page at least once (`lib/haptics.ts`).
   */
  haptic?: boolean;
}

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  fullWidth = false,
  haptic,
  className,
  children,
  disabled,
  onPointerDown,
  ...props
}: ButtonProps) {
  const wantsHaptic = haptic ?? variant === "primary";

  function handlePointerDown(event: PointerEvent<HTMLButtonElement>) {
    if (wantsHaptic && !disabled && !loading) haptics.tick();
    onPointerDown?.(event);
  }

  return (
    <button
      className={cn(
        // `.press` (globals.css §2.3) owns `transform`: compress on contact
        // (90ms, no bounce) and spring back with overshoot on release (260ms).
        // One owner on purpose — a Tailwind `active:scale-*` alongside it would
        // fight it in the cascade and produce a coin-flip of the two feels.
        "press inline-flex select-none items-center justify-center gap-2 font-medium disabled:pointer-events-none disabled:opacity-50",
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        fullWidth && "w-full",
        className,
      )}
      disabled={disabled || loading}
      onPointerDown={handlePointerDown}
      {...props}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
      {children}
    </button>
  );
}
