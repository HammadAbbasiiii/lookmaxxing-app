"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Compass, Home, ListChecks, MessageCircle, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { PRIMARY_TABS, isTabActive } from "@/lib/nav";

/** Icons for the shared tab list — hrefs and labels live in lib/nav.ts (§7.2). */
const TAB_ICONS = {
  "/dashboard": Home,
  "/plan": ListChecks,
  "/coach": MessageCircle,
  "/glow": Sparkles,
  "/explore": Compass,
} as const;

/** Mobile bottom tab bar (§7.2). Active tab is gold, inactive is muted. */
export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border-soft bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
      aria-label="Bottom"
    >
      <div className="mx-auto grid max-w-md grid-cols-5">
        {PRIMARY_TABS.map((tab) => {
          const active = isTabActive(pathname, tab.href);
          const Icon = TAB_ICONS[tab.href];
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                "flex min-w-0 flex-col items-center gap-1 overflow-hidden px-0.5 py-2.5 text-[11px] font-medium leading-none transition-colors",
                active ? "text-gold" : "text-muted hover:text-ink",
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon className="h-5 w-5 shrink-0" aria-hidden />
              <span className="w-full truncate text-center">{tab.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
