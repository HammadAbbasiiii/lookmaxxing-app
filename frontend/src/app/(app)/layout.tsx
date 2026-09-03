"use client";

import type { ReactNode } from "react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { AppShell } from "@/components/layout/AppShell";
import { Spinner } from "@/components/ui/Skeleton";

export default function AppLayout({ children }: { children: ReactNode }) {
  const ready = useRequireAuth();

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  return <AppShell>{children}</AppShell>;
}
