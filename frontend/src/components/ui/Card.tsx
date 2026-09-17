import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /**
   * The card is (or contains) a link to somewhere else: it gets the full
   * physical treatment — press compression on contact, a spring-back release,
   * and a pointer-fine hover lift (globals.css §2.3). Only mark cards that are
   * genuinely tappable, so the physics stays honest.
   */
  interactive?: boolean;
}

export function Card({ className, interactive = false, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "card-border rounded-card p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.04),0_12px_32px_-16px_rgba(0,0,0,0.7)]",
        interactive && "press lift cursor-pointer hover:border-gold/40",
        className,
      )}
      {...props}
    />
  );
}

export function CardTitle({
  className,
  ...props
}: HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("text-lg font-semibold text-ink", className)} {...props} />;
}
