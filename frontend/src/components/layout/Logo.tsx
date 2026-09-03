import Link from "next/link";
import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <Link
      href="/"
      className={cn(
        "inline-flex items-center gap-2 font-display text-lg font-bold tracking-tight text-ink",
        className,
      )}
    >
      <span className="flex h-7 w-7 items-center justify-center rounded-lg gold-gradient text-sm font-black text-black">
        L
      </span>
      <span>
        Look<span className="text-gold">Maxx</span>
      </span>
    </Link>
  );
}
