"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { track } from "@/lib/api/analytics";

/** Map key routes to semantic intent events (feeds the admin funnel / User 360). */
function semanticEventsFor(path: string): string[] {
  const events: string[] = [];
  if (path === "/upgrade" || path.startsWith("/upgrade")) events.push("pricing_viewed");
  if (path.startsWith("/products")) events.push("products_browsed");
  if (path.startsWith("/plan")) events.push("plan_viewed");
  if (path.startsWith("/progress")) events.push("progress_viewed");
  if (path.startsWith("/results")) events.push("results_viewed");
  if (path.startsWith("/upload")) events.push("upload_started");
  if (path.startsWith("/explore")) events.push("explore_viewed");
  if (path.startsWith("/dashboard")) {
    events.push("dashboard_viewed");
    events.push("gallery_opened"); // dashboard renders the user's photo gallery
  }
  return events;
}

/**
 * Mount once at the root. Records session_start, page_view, and page_exit
 * (with dwell time) for every route — the backbone of the admin funnel view —
 * plus semantic intent events for key routes (pricing, plan, products, …).
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
    for (const ev of semanticEventsFor(pathname)) track(ev, { page: pathname });
    prevPath.current = pathname;
    startRef.current = Date.now();
  }, [pathname]);

  return null;
}
