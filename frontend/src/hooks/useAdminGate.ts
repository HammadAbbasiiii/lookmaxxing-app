"use client";

import { useRequireAuth } from "@/hooks/useRequireAuth";
import { useMe } from "@/hooks/useMe";

export type AdminGate = "loading" | "denied" | "allowed";

/**
 * Admin route gate. Reuses `useRequireAuth` for the token/401 handling, then
 * checks `is_admin` from the shared `/auth/me` query. The `/auth/me` result is
 * deduped (queryKey `["me"]`), so this does not double-fetch.
 */
export function useAdminGate(): AdminGate {
  const authed = useRequireAuth();
  const me = useMe(authed);

  if (!authed) return "loading";
  if (me.isLoading) return "loading";
  if (me.isError) return "denied";
  return me.data?.is_admin === true ? "allowed" : "denied";
}
