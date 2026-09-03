"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { ArrowLeft } from "lucide-react";
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
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4">
          <Link href="/admin" className="font-display text-sm font-semibold text-gold">
            LookMaxx Admin
          </Link>
          <nav className="flex gap-1 overflow-x-auto">
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
          <Link
            href="/dashboard"
            className="ml-auto flex shrink-0 items-center gap-1.5 rounded-lg border border-border-soft px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:border-gold/40 hover:text-ink"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> View app as user
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}
