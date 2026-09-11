"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  CreditCard,
  LayoutDashboard,
  LogOut,
  Settings as SettingsIcon,
  User as UserIcon,
} from "lucide-react";
import { useMe } from "@/hooks/useMe";
import { logout } from "@/lib/api/endpoints";
import { clearToken } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { isActivePath, isGlowPath } from "@/lib/nav";
import { Logo } from "./Logo";
import { Badge } from "@/components/ui/Badge";
import { AvatarDrawer } from "./AvatarDrawer";
import { NotificationBell } from "./NotificationBell";

const PRIMARY_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/plan", label: "Plan" },
  { href: "/coach", label: "Coach" },
  { href: "/glow", label: "Glow" },
  { href: "/explore", label: "Explore" },
];

export function TopNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { data: user } = useMe();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const tier = user?.subscription_tier ?? "free";
  const isFree = tier === "free";
  const isAdmin = user?.is_admin === true;

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  // Close menus whenever the route changes.
  useEffect(() => {
    setMenuOpen(false);
    setDrawerOpen(false);
  }, [pathname]);

  async function handleSignOut() {
    setMenuOpen(false);
    setDrawerOpen(false);
    await logout().catch(() => {});
    clearToken();
    router.replace("/");
  }

  function go(href: string) {
    setMenuOpen(false);
    router.push(href);
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border-soft bg-background/90 pt-[env(safe-area-inset-top,0px)] backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between gap-2 px-4 md:gap-3">
        <Logo className="shrink-0" />

        <nav className="no-scrollbar hidden min-w-0 flex-1 overflow-x-auto md:block" aria-label="Primary">
          <div className="flex min-w-max items-center gap-0.5 px-2">
            {PRIMARY_LINKS.map((link) => {
              const active =
                link.href === "/glow"
                  ? isGlowPath(pathname)
                  : isActivePath(pathname, link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "shrink-0 whitespace-nowrap rounded-lg px-2.5 py-2 text-sm font-medium transition-colors",
                    active ? "text-ink" : "text-muted hover:text-ink",
                  )}
                  aria-current={active ? "page" : undefined}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>
        </nav>

        <div className="flex shrink-0 items-center gap-2">
          {isAdmin ? (
            <Link href="/admin" className="hidden shrink-0 md:block">
              <Badge variant="outline" className="cursor-pointer whitespace-nowrap border-gold/40 text-gold hover:opacity-90">
                <LayoutDashboard className="h-3.5 w-3.5" /> Admin
              </Badge>
            </Link>
          ) : null}

          {isFree ? (
            <Link href="/upgrade" className="hidden shrink-0 md:block">
              <Badge variant="gold" className="cursor-pointer whitespace-nowrap hover:opacity-90">
                Upgrade
              </Badge>
            </Link>
          ) : (
            <Badge variant="gold" className="hidden whitespace-nowrap md:flex">
              {tier === "elite" ? "Elite" : "Pro"}
            </Badge>
          )}

          <NotificationBell />

          {/* Desktop avatar -> dropdown */}
          <div className="relative hidden md:block" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen((o) => !o)}
              className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-2 text-sm font-semibold text-ink ring-1 ring-border-soft transition-colors hover:ring-gold/40"
              aria-label="Account menu"
              aria-expanded={menuOpen}
            >
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : <UserIcon className="h-4 w-4" />}
            </button>

            {menuOpen ? (
              <div className="absolute right-0 top-11 w-56 overflow-hidden rounded-xl card-border shadow-lg">
                <div className="border-b border-border-soft px-4 py-3">
                  <p className="truncate text-sm font-medium text-ink">{user?.full_name || "Member"}</p>
                  <p className="truncate text-xs text-muted">{user?.email}</p>
                </div>

                {isAdmin ? (
                  <button
                    type="button"
                    onClick={() => go("/admin")}
                    className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-ink hover:bg-surface-2"
                  >
                    <LayoutDashboard className="h-4 w-4 text-gold" /> Admin Dashboard
                  </button>
                ) : null}

                <button
                  type="button"
                  onClick={() => go("/settings")}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-ink hover:bg-surface-2"
                >
                  <UserIcon className="h-4 w-4 text-muted" /> Profile
                </button>
                <button
                  type="button"
                  onClick={() => go("/settings")}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-ink hover:bg-surface-2"
                >
                  <SettingsIcon className="h-4 w-4 text-muted" /> Settings
                </button>
                <button
                  type="button"
                  onClick={() => go(isFree ? "/upgrade" : "/settings")}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-ink hover:bg-surface-2"
                >
                  <CreditCard className="h-4 w-4 text-muted" /> {isFree ? "Upgrade" : "Subscription"}
                </button>

                <button
                  type="button"
                  onClick={handleSignOut}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-danger hover:bg-surface-2"
                >
                  <LogOut className="h-4 w-4" /> Sign out
                </button>
              </div>
            ) : null}
          </div>

          {/* Mobile avatar -> drawer */}
          <button
            type="button"
            onClick={() => setDrawerOpen(true)}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-2 text-sm font-semibold text-ink ring-1 ring-border-soft transition-colors hover:ring-gold/40 md:hidden"
            aria-label="Account menu"
          >
            {user?.full_name ? user.full_name.charAt(0).toUpperCase() : <UserIcon className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <AvatarDrawer open={drawerOpen} onClose={() => setDrawerOpen(false)} />
    </header>
  );
}
