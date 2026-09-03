"use client";

import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";

interface ScreenHeaderProps {
  title: string;
  subtitle?: string;
  back?: boolean;
  backHref?: string;
  action?: ReactNode;
  className?: string;
}

export function ScreenHeader({
  title,
  subtitle,
  back = false,
  backHref,
  action,
  className,
}: ScreenHeaderProps) {
  const router = useRouter();

  return (
    <header className={cn("mb-6", className)}>
      {back ? (
        <button
          type="button"
          onClick={() => (backHref ? router.push(backHref) : router.back())}
          className="mb-3 inline-flex items-center gap-1 text-sm text-muted transition-colors hover:text-ink"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </button>
      ) : null}
      <div className="flex items-end justify-between gap-4">
        <div>
          <span className="mb-2 block h-1 w-10 rounded-full gold-gradient" aria-hidden />
          <h1 className="font-display text-2xl font-bold text-ink md:text-3xl">{title}</h1>
          {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    </header>
  );
}
