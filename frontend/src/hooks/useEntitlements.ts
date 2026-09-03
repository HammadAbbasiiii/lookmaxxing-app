"use client";

import { useQuery } from "@tanstack/react-query";
import { getEntitlements } from "@/lib/api/endpoints";
import { STALE } from "@/lib/constants";

/** Shared `/entitlements` query — server-authoritative tier + feature flags. */
export function useEntitlements(enabled = true) {
  return useQuery({
    queryKey: ["entitlements"],
    queryFn: getEntitlements,
    enabled,
    staleTime: STALE.dashboard,
    gcTime: 5 * 60 * 1000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
