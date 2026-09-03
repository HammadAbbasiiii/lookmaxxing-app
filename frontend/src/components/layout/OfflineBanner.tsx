"use client";

import { useOnline } from "@/hooks/useOnline";

/** Persistent thin banner shown only while offline (§7.2). */
export function OfflineBanner() {
  const online = useOnline();
  if (online) return null;

  return (
    <div className="sticky top-0 z-50 border-b border-warning/20 bg-warning/15 px-4 py-1.5 text-center text-xs text-warning">
      You're offline — we'll sync when you're back.
    </div>
  );
}
