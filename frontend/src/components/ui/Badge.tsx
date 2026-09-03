import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type Variant = "gold" | "muted" | "success" | "warning" | "danger" | "outline";

const VARIANT_CLASSES: Record<Variant, string> = {
  gold: "bg-gold/15 text-gold-bright border border-gold/30",
  muted: "bg-surface-2 text-muted border border-border-soft",
  success: "bg-success/15 text-success border border-success/30",
  warning: "bg-warning/15 text-warning border border-warning/30",
  danger: "bg-danger/15 text-danger border border-danger/30",
  outline: "bg-transparent text-muted border border-border-soft",
};

export function Badge({
  variant = "muted",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
        VARIANT_CLASSES[variant],
        className,
      )}
      {...props}
    />
  );
}
