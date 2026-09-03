"use client";

import { useQuery } from "@tanstack/react-query";
import { getMe } from "@/lib/api/endpoints";
import { STALE } from "@/lib/constants";

/**
 * Shared `/auth/me` query. `staleTime: 0` means the user/tier is always fresh
 * (§20.5 — gating reads are never stale-cached), but the result is still
 * deduped within a render pass so we don't hammer the backend.
 */
export function useMe(enabled = true) {
  return useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    enabled,
    staleTime: STALE.me,
    gcTime: 5 * 60 * 1000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
