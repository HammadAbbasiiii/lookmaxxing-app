"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Compass,
  Home,
  ListChecks,
  Settings as SettingsIcon,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/plan", label: "Plan", icon: ListChecks },
  { href: "/glow-up", label: "Glow-Up", icon: Sparkles },
  { href: "/progress", label: "Progress", icon: TrendingUp },
  { href: "/explore", label: "Explore", icon: Compass },
  { href: "/settings", label: "Settings", icon: SettingsIcon },
];

/** Mobile bottom tab bar (§7.2). Active tab is gold, inactive is muted. */
export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border-soft bg-background/95 backdrop-blur md:hidden"
      aria-label="Bottom"
    >
      <div className="mx-auto grid max-w-md grid-cols-6">
        {TABS.map((tab) => {
          const active = pathname.startsWith(tab.href);
          const Icon = tab.icon;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                "flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium transition-colors",
                active ? "text-gold" : "text-muted hover:text-ink",
              )}
              aria-current={active ? "page" : undefined}
            >
              <Icon className="h-5 w-5" aria-hidden />
              {tab.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
