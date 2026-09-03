"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { clearToken, getToken, UNAUTHORIZED_EVENT } from "@/lib/auth";
import { ApiError } from "@/lib/api/client";
import { useMe } from "@/hooks/useMe";

/**
 * Global route guard (§7.3 #1). Redirects to /login only when the token is
 * missing OR the server reports 401 (expired/invalid). A network error is NOT
 * treated as a logout — screens render their own offline/retry states instead.
 *
 * The token lives in localStorage, which is unavailable during SSR. We start in
 * an "unknown" state (null) on BOTH server and client so the first render is
 * identical (no hydration mismatch), then resolve the real value in an effect.
 */
export function useRequireAuth(): boolean {
  const router = useRouter();
  const pathname = usePathname();
  const [hasToken, setHasToken] = useState<boolean | null>(null);
  const me = useMe(hasToken === true);

  const authFailed =
    me.isError && me.error instanceof ApiError && me.error.status === 401;

  // Resolve the token once, on the client only. Redirect immediately if absent.
  useEffect(() => {
    const token = Boolean(getToken());
    setHasToken(token);
    if (!token) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [router, pathname]);

  // Listen for 401s (expired/invalid token) and bounce to /login.
  useEffect(() => {
    if (hasToken !== true) return;
    const redirect = () => {
      clearToken();
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    };
    if (authFailed) redirect();
    window.addEventListener(UNAUTHORIZED_EVENT, redirect);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, redirect);
  }, [hasToken, authFailed, router, pathname]);

  // Not "ready" until we've confirmed a token on the client.
  return hasToken === true && !authFailed;
}

