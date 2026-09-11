"use client";

import type { ReactNode } from "react";
import { TopNav } from "./TopNav";
import { GlowSubNav } from "./GlowSubNav";
import { BottomNav } from "./BottomNav";
import { OfflineBanner } from "./OfflineBanner";
import { AdminModeBanner } from "./AdminModeBanner";

/** Authenticated app shell: top nav (desktop) + bottom tabs (mobile). */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <OfflineBanner />
      <TopNav />
      <GlowSubNav />
      <AdminModeBanner />
      <main className="mx-auto w-full max-w-5xl px-5 pb-28 pt-4 md:pb-16 md:pt-6">
        {children}
      </main>
      <BottomNav />
    </div>
  );
}
