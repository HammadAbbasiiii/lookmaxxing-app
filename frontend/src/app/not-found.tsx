import Link from "next/link";
import { Button } from "@/components/ui/Button";

/** Branded 404 — never a blank screen (§7.3 #5). */
export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 text-center">
      <p className="text-sm font-semibold text-gold">404</p>
      <h1 className="mt-2 font-display text-3xl font-bold text-ink">Page not found</h1>
      <p className="mt-2 max-w-sm text-sm text-muted">
        The page you&apos;re looking for doesn&apos;t exist or was moved.
      </p>
      <Link href="/dashboard" className="mt-6">
        <Button>Back to dashboard</Button>
      </Link>
    </div>
  );
}
