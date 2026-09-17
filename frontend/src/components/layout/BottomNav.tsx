"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Compass, Home, ListChecks, MessageCircle, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { PRIMARY_TABS, isTabActive, navTier } from "@/lib/nav";
import { LockChip } from "@/components/ui/LockChip";

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
          const tier = navTier(tab.href);
          const Icon = TAB_ICONS[tab.href];
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                // `.press`: on a phone the tab bar is the most-tapped surface in
                // the app, so it gets the same contact/release physics as every
                // other actionable thing (§2.3). `touch-action: manipulation`
                // (global) already removed the 300ms double-tap delay.
                "press flex min-w-0 flex-col items-center gap-1 overflow-hidden px-0.5 py-2.5 text-[11px] font-medium leading-none",
                active ? "text-gold" : "text-muted hover:text-ink",
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon className="h-5 w-5 shrink-0" aria-hidden />
              <span className="flex w-full items-center justify-center gap-0.5">
                <span className="truncate text-center">{tab.label}</span>
                {/* A padlock keeps "Coach needs Pro" visible without spelling Pro
                    out — there is no room in a 5-tab bar on a 375px screen. The
                    chip's sr-only text keeps the accessible name as "Coach Pro". */}
                {tier ? <LockChip tier={tier} iconOnly bare className="shrink-0 gap-0" /> : null}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
