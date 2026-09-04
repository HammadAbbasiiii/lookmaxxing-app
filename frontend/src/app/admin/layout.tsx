"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ArrowLeft, Menu, X } from "lucide-react";
import { useAdminGate } from "@/hooks/useAdminGate";
import { Spinner } from "@/components/ui/Skeleton";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/admin", label: "Dashboard" },
  { href: "/admin/users", label: "Users" },
  { href: "/admin/products", label: "Products" },
  { href: "/admin/analytics", label: "Analytics" },
  { href: "/admin/activity", label: "Activity" },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  const gate = useAdminGate();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close the mobile menu on outside click (mirrors TopNav behaviour).
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  // Close the mobile menu whenever the route changes.
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  if (gate === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  if (gate === "denied") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <div className="card-border rounded-card max-w-md p-8 text-center">
          <h1 className="text-xl font-semibold text-ink">Admin access required</h1>
          <p className="mt-2 text-sm text-muted">
            This area is restricted to administrators. Your account does not have access.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 border-b border-border-soft bg-background/90 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4">
          <div className="flex h-14 items-center gap-2">
            <Link href="/admin" className="shrink-0 font-display text-sm font-semibold text-gold">
              LookMaxx Admin
            </Link>

            {/* Desktop nav — inline links, no horizontal scrolling. */}
            <nav className="ml-2 hidden min-w-0 flex-1 items-center gap-1 md:flex" aria-label="Admin">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "whitespace-nowrap rounded-lg px-3 py-1.5 text-sm",
                    pathname === item.href
                      ? "bg-surface-2 text-ink"
                      : "text-muted hover:text-ink",
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </nav>

            {/* Mobile spacer pushes the actions right; no scrollbar involved. */}
            <div className="min-w-0 flex-1 md:hidden" />

            <Link
              href="/dashboard"
              className="flex shrink-0 items-center gap-1.5 rounded-lg border border-border-soft px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:border-gold/40 hover:text-ink"
            >
              <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
              <span>View app as user</span>
            </Link>

            {/* Mobile hamburger — same dropdown pattern as the client TopNav. */}
            <div className="relative md:hidden" ref={menuRef}>
              <button
                type="button"
                onClick={() => setMenuOpen((o) => !o)}
                className="flex h-9 w-9 items-center justify-center rounded-lg bg-surface-2 text-ink ring-1 ring-border-soft transition-colors hover:ring-gold/40"
                aria-label="Admin menu"
                aria-expanded={menuOpen}
              >
                {menuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
              </button>

              {menuOpen ? (
                <nav
                  className="absolute right-0 top-11 w-56 overflow-hidden rounded-xl card-border shadow-lg"
                  aria-label="Admin mobile"
                >
                  <div className="p-2">
                    {NAV.map((item) => (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={() => setMenuOpen(false)}
                        className={cn(
                          "block rounded-lg px-3 py-2.5 text-sm font-medium",
                          pathname === item.href
                            ? "bg-surface-2 text-ink"
                            : "text-muted hover:bg-surface-2 hover:text-ink",
                        )}
                      >
                        {item.label}
                      </Link>
                    ))}
                    <Link
                      href="/dashboard"
                      onClick={() => setMenuOpen(false)}
                      className="mt-1 flex items-center gap-1.5 rounded-lg px-3 py-2.5 text-sm font-medium text-muted hover:bg-surface-2 hover:text-ink"
                    >
                      <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
                      View app as user
                    </Link>
                  </div>
                </nav>
              ) : null}
            </div>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}
