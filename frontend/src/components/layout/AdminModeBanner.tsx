"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, ShieldCheck } from "lucide-react";
import { useMe } from "@/hooks/useMe";

/**
 * The "admin sign" shown while an admin is browsing the *user* app.
 *
 * Admins share one account for both roles, so this thin strip makes the active
 * admin status visible on every user screen and gives a one-tap path back into
 * the admin dashboard — the mirror image of the "Admin" badge in TopNav that
 * takes you from user → admin. Hidden inside /admin (the admin layout has its
 * own "View app as user" return link).
 */
export function AdminModeBanner() {
  const pathname = usePathname();
  const { data: user } = useMe();

  if (user?.is_admin !== true) return null;
  if (pathname.startsWith("/admin")) return null;

  return (
    <div className="border-b border-gold/20 bg-gold/10">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-3 px-4 py-1.5">
        <div className="flex items-center gap-2 text-xs">
          <ShieldCheck className="h-4 w-4 text-gold" aria-hidden />
          <span className="font-semibold uppercase tracking-wide text-gold-bright">Admin</span>
          <span className="text-muted">· browsing as user</span>
        </div>
        <Link
          href="/admin"
          className="flex items-center gap-1.5 text-xs font-medium text-gold-bright hover:underline"
        >
          <LayoutDashboard className="h-3.5 w-3.5" aria-hidden /> Admin dashboard
        </Link>
      </div>
    </div>
  );
}
