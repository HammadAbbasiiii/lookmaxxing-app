"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Settings as SettingsIcon, User as UserIcon } from "lucide-react";
import { useMe } from "@/hooks/useMe";
import { logout } from "@/lib/api/endpoints";
import { clearToken } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Logo } from "./Logo";
import { Badge } from "@/components/ui/Badge";

const LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/plan", label: "Plan" },
  { href: "/progress", label: "Progress" },
  { href: "/explore", label: "Explore" },
  { href: "/products", label: "Products" },
];

export function TopNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { data: user } = useMe();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const tier = user?.subscription_tier ?? "free";
  const isFree = tier === "free";

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  async function handleSignOut() {
    setMenuOpen(false);
    await logout().catch(() => {});
    clearToken();
    router.replace("/");
  }

  return (
    <header className="sticky top-0 z-40 border-b border-border-soft bg-background/90 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between px-4">
        <Logo />

        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
          {LINKS.map((link) => {
            const active = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  active ? "text-ink" : "text-muted hover:text-ink",
                )}
                aria-current={active ? "page" : undefined}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          {isFree ? (
            <Link href="/upgrade" className="hidden md:block">
              <Badge variant="gold" className="cursor-pointer hover:opacity-90">
                Upgrade
              </Badge>
            </Link>
          ) : (
            <Badge variant="gold" className="hidden md:flex">
              {tier === "elite" ? "Elite" : "Pro"}
            </Badge>
          )}

          <div className="relative" ref={menuRef}>
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
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    router.push("/settings");
                  }}
                  className="flex w-full items-center gap-2 px-4 py-2.5 text-sm text-ink hover:bg-surface-2"
                >
                  <SettingsIcon className="h-4 w-4 text-muted" /> Settings
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
        </div>
      </div>
    </header>
  );
}
