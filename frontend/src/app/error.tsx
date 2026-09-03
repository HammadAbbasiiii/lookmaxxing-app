"use client";

import { useEffect } from "react";
import { ErrorCard } from "@/components/ui/ErrorCard";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[app error boundary]", error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <ErrorCard
        title="Something went wrong"
        message="Something went wrong. Reload to continue."
        onRetry={reset}
        actionLabel="Reload"
      />
    </div>
  );
}
