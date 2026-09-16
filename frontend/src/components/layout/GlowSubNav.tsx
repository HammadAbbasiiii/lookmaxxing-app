"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { GLOW_LINKS, isActivePath, isGlowPath, navTier } from "@/lib/nav";
import { LockChip } from "@/components/ui/LockChip";

/** Contextual sub-tabs for the Glow section, shown on every Glow-related page. */
export function GlowSubNav() {
  const pathname = usePathname();

  if (!isGlowPath(pathname)) return null;

  return (
    <nav className="border-b border-border-soft bg-background" aria-label="Glow">
      <div className="no-scrollbar mx-auto flex w-full max-w-5xl items-center gap-1 overflow-x-auto px-4 py-2">
        {GLOW_LINKS.map((link) => {
          const active = isActivePath(pathname, link.href);
          const tier = navTier(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1.5 text-sm font-medium transition-colors",
                active ? "bg-gold/15 text-gold-bright" : "text-muted hover:text-ink",
              )}
              aria-current={active ? "page" : undefined}
            >
              {link.label}
              {/* Insights and Simulator ask for Pro on arrival — say so up front. */}
              {tier ? <LockChip tier={tier} /> : null}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
