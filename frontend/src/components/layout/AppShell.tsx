"use client";

import type { ReactNode } from "react";
import { TopNav } from "./TopNav";
import { BottomNav } from "./BottomNav";
import { OfflineBanner } from "./OfflineBanner";

/** Authenticated app shell: top nav (desktop) + bottom tabs (mobile). */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <OfflineBanner />
      <TopNav />
      <main className="mx-auto w-full max-w-5xl px-4 pb-28 pt-6 md:pb-16 md:pt-8">
        {children}
      </main>
      <BottomNav />
    </div>
  );
}
