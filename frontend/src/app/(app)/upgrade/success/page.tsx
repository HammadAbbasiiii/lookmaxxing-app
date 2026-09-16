"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Check, Crown, Receipt } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Skeleton } from "@/components/ui/Skeleton";
import { getCheckoutSession } from "@/lib/api/endpoints";
import { normalizeTier, tierLabel } from "@/lib/tiers";

/**
 * Post-checkout receipt (DEF-015).
 *
 * Stripe redirects here with `?session_id=...` (see `success_url` in
 * `payments.create_checkout`). Every amount on this page is read back from
 * Stripe for that session — the app's own constants are never used — so the
 * confirmation can't contradict the invoice. Previously nothing handled the
 * redirect at all (`/dashboard?upgraded=1`), so a user who paid £1 landed on a
 * page still quoting £9.99.
 */
function gbp(amount: number): string {
  return `£${amount.toFixed(2)}`;
}

function formatDate(value: string | null | undefined): string | null {
  if (!value) return null;
  // The API returns naive UTC ISO strings; anchor them so the date doesn't
  // drift by a day for users behind UTC.
  const iso = /[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}

function ReceiptContent() {
  const params = useSearchParams();
  const sessionId = params.get("session_id");

  const receipt = useQuery({
    queryKey: ["checkout-session", sessionId],
    queryFn: () => getCheckoutSession(sessionId as string),
    enabled: Boolean(sessionId),
    retry: 1,
    staleTime: 30_000,
  });

  if (!sessionId) {
    return (
      <Neutral
        title="Welcome aboard"
        message="Your plan is active. If you've just paid, your receipt will arrive by email."
      />
    );
  }

  if (receipt.isLoading) {
    return (
      <div className="mx-auto max-w-md pt-10">
        <Skeleton className="h-6 w-40" />
        <Skeleton className="mt-4 h-32 w-full" />
      </div>
    );
  }

  if (receipt.isError) {
    return (
      <Neutral
        title="You're all set"
        message="We couldn't load the payment receipt just now — check your email for the Stripe confirmation. Your plan is already active."
      />
    );
  }

  const r = receipt.data;
  if (!r) {
    return (
      <Neutral
        title="You're all set"
        message="We couldn't load the payment receipt just now — check your email for the Stripe confirmation."
      />
    );
  }
  const charged = r.amount_charged;
  const nextAmount = r.next_payment_amount;
  const nextDate = formatDate(r.next_payment_date);
  const planName = tierLabel(normalizeTier(r.tier));

  return (
    <div className="mx-auto max-w-md">
      <ScreenHeader title="Payment confirmed" subtitle="Here's exactly what you were charged." />

      <div className="card-border rounded-card p-6 text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-gold/15">
          {r.paid ? (
            <Check className="h-6 w-6 text-gold" aria-hidden />
          ) : (
            <Receipt className="h-6 w-6 text-gold" aria-hidden />
          )}
        </div>
        <h1 className="mt-4 flex items-center justify-center gap-2 font-display text-2xl font-bold text-ink">
          {planName}
          <Crown className="h-4 w-4 text-gold" aria-hidden />
        </h1>
        <p className="mt-2 text-sm text-muted">
          {r.paid
            ? r.first_month_offer
              ? `You were charged${charged != null ? ` ${gbp(charged)}` : ""} for your first month.`
              : `You were charged${charged != null ? ` ${gbp(charged)}` : ""} — your ${planName} plan is active.`
            : "Stripe is confirming your payment — this usually takes a few seconds."}
        </p>

        <dl className="mt-6 space-y-2 text-left text-sm">
          {charged != null ? (
            <div className="flex items-center justify-between">
              <dt className="text-muted">Charged today</dt>
              <dd className="tabular font-semibold text-ink">{gbp(charged)}</dd>
            </div>
          ) : null}
          {r.amount_discount ? (
            <div className="flex items-center justify-between">
              <dt className="text-muted">Discount applied</dt>
              <dd className="tabular font-medium text-success">−{gbp(r.amount_discount)}</dd>
            </div>
          ) : null}
          {nextAmount != null ? (
            <div className="flex items-center justify-between">
              <dt className="text-muted">
                Next payment{nextDate ? ` (${nextDate})` : ""}
              </dt>
              <dd className="tabular font-semibold text-ink">
                {gbp(nextAmount)}
                {r.interval === "year" ? "/yr" : "/mo"}
              </dd>
            </div>
          ) : null}
        </dl>

        {r.email ? (
          <p className="mt-4 text-xs text-muted">A receipt is on its way to {r.email}.</p>
        ) : null}
      </div>

      <Link href="/dashboard" className="mt-6 block">
        <Button variant="primary" fullWidth>
          Go to your dashboard
        </Button>
      </Link>
      <Link
        href="/settings"
        className="mt-3 block text-center text-xs text-muted underline underline-offset-2"
      >
        Manage subscription
      </Link>
    </div>
  );
}

function Neutral({ title, message }: { title: string; message: string }) {
  return (
    <div className="mx-auto max-w-md pt-10 text-center">
      <ScreenHeader title={title} />
      <p className="text-sm text-muted">{message}</p>
      <Link href="/dashboard" className="mt-6 block">
        <Button variant="primary" fullWidth>
          Go to your dashboard
        </Button>
      </Link>
    </div>
  );
}

export default function CheckoutSuccessPage() {
  // `useSearchParams` needs a Suspense boundary so the route can still be
  // statically analysed by the Next.js build.
  return (
    <Suspense fallback={<Skeleton className="mx-auto mt-10 h-32 w-full max-w-md" />}>
      <ReceiptContent />
    </Suspense>
  );
}
