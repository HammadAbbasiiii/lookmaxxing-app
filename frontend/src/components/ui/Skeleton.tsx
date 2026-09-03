import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/** Skeleton block that matches final layout (zero layout shift, §10). */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("shimmer rounded-lg", className)} aria-hidden />;
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn("h-5 w-5 animate-spin text-gold", className)} aria-hidden />;
}
