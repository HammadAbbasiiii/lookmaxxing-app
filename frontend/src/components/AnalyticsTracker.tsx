"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { track } from "@/lib/api/analytics";

/**
 * Mount once at the root. Records session_start, page_view, and page_exit
 * (with dwell time) for every route — the backbone of the admin funnel view.
 */
export function AnalyticsTracker() {
  const pathname = usePathname();
  const startRef = useRef(Date.now());
  const prevPath = useRef<string | null>(null);

  useEffect(() => {
    track("session_start");
    const end = () =>
      track("session_end", { metadata: { duration_ms: Date.now() - startRef.current } });
    window.addEventListener("beforeunload", end);
    return () => window.removeEventListener("beforeunload", end);
  }, []);

  useEffect(() => {
    const prev = prevPath.current;
    if (prev !== null && prev !== pathname) {
      track("page_exit", { page: prev, metadata: { duration_ms: Date.now() - startRef.current } });
    }
    track("page_view", { page: pathname });
    prevPath.current = pathname;
    startRef.current = Date.now();
  }, [pathname]);

  return null;
}
