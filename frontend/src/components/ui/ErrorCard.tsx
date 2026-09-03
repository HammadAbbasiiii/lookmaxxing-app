import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface ErrorCardProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  actionLabel?: string;
}

/** Friendly retry card — never a blank red screen (§9.1, §10). */
export function ErrorCard({
  title = "Something went wrong",
  message,
  onRetry,
  actionLabel = "Try again",
}: ErrorCardProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-card border border-danger/20 bg-surface px-6 py-12 text-center">
      <AlertTriangle className="mb-3 h-8 w-8 text-warning" aria-hidden />
      <h3 className="text-base font-semibold text-ink">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-muted">{message}</p>
      {onRetry ? (
        <Button variant="secondary" className="mt-5" onClick={onRetry}>
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
}
