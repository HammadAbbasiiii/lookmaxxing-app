"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Check, Crown, Gift, ShieldCheck, Zap } from "lucide-react";
import { toast } from "sonner";
import { useMe } from "@/hooks/useMe";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import {
  ANNUAL_DISCOUNT_PCT,
  ELITE_TRIAL_DAYS,
  FIRST_MONTH_PRICE,
  PLAN_ORDER,
  PLANS,
} from "@/lib/constants";
import { cn } from "@/lib/utils";
import { track } from "@/lib/api/analytics";
import { changePlan, createCheckout } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";

export default function UpgradePage() {
  const [annual, setAnnual] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const router = useRouter();
  const qc = useQueryClient();
  const { data: user } = useMe();
  const tier = user?.subscription_tier ?? "free";

  // The iOS "AppState" flag maps here: /auth/me carries the server-authoritative
  // has_used_first_month_offer, which prevents the £1 first month being reused
  // (loss aversion — a user who's already "invested" is more likely to stay).
  const firstMonthEligible =
    tier === "free" && user?.has_used_first_month_offer === false;

  function gbp(amount: number): string {
    return `£${amount.toFixed(2)}`;
  }

  function waitlistMessage(name: string, email?: string): string {
    return `You're on the ${name} waitlist — we'll email ${email || "you"} when it launches.`;
  }

  async function startFirstMonth() {
    track("upgrade_click", { metadata: { tier: "pro", plan: "Pro", first_month_offer: true } });
    setBusy("first-month");
    try {
      const res = await createCheckout("pro", false, true);
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      } else {
        toast.info(waitlistMessage("Pro", user?.email));
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) {
        toast.info(waitlistMessage("Pro", user?.email));
      } else {
        toast.error(e instanceof ApiError ? e.message : "Couldn't start checkout. Try again.");
      }
    } finally {
      setBusy(null);
    }
  }

  async function handleSelect(planKey: keyof typeof PLANS) {
    const plan = PLANS[planKey];
    if (plan.tier === "free") {
      router.push("/dashboard");
      return;
    }
    track("upgrade_click", { metadata: { tier: plan.tier, plan: plan.name } });
    if (tier === plan.tier) {
      toast.info(`You're already on ${plan.name}.`);
      return;
    }

    setBusy(plan.tier);
    try {
      // Existing subscriber → swap plans in place (Stripe prorates) instead of
      // opening a second checkout, so access never lapses mid-switch.
      if (tier !== "free") {
        const res = await changePlan(plan.tier as "pro" | "elite", annual);
        if (res.success) {
          toast.success(`Switched to ${plan.name}.`);
          qc.invalidateQueries({ queryKey: ["me"] });
        } else {
          toast.error("Couldn't change your plan. Try again.");
        }
        return;
      }

      const res = await createCheckout(plan.tier as "pro" | "elite", annual);
      if (res.checkout_url) {
        window.location.href = res.checkout_url;
      } else {
        toast.info(waitlistMessage(plan.name, user?.email));
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) {
        // Payments not configured → honest waitlist fallback (§12.4).
        toast.info(waitlistMessage(plan.name, user?.email));
      } else {
        toast.error(e instanceof ApiError ? e.message : "Couldn't start checkout. Try again.");
      }
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <ScreenHeader
        title="Upgrade"
        subtitle={
          tier !== "free"
            ? "You're already on " + (tier === "elite" ? "Elite" : "Pro") + "."
            : "Keep your streak & history synced. Cancel anytime."
        }
      />

      {/* £1 first-month offer (low barrier + loss aversion: already "invested") */}
      {firstMonthEligible ? (
        <div className="mb-6 rounded-card border border-gold/40 bg-gold/10 p-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <Gift className="mt-0.5 h-5 w-5 shrink-0 text-gold" aria-hidden />
              <div>
                <p className="font-display text-lg font-bold text-ink">
                  Get started for £{FIRST_MONTH_PRICE}
                </p>
                <p className="mt-1 text-sm text-muted">
                  Your first month is just £{FIRST_MONTH_PRICE}, then £9.99/month. Cancel anytime.
                </p>
              </div>
            </div>
            <Button
              onClick={startFirstMonth}
              variant="primary"
              loading={busy === "first-month"}
              disabled={busy !== null}
              className="shrink-0"
            >
              Start for £{FIRST_MONTH_PRICE}
            </Button>
          </div>
        </div>
      ) : null}

      {/* Annual / monthly toggle (anchor) */}
      <div className="mb-6 flex justify-center">
        <div className="inline-flex rounded-full border border-border-soft bg-surface-2 p-1">
          {(["monthly", "annual"] as const).map((mode) => {
            const active = annual === (mode === "annual");
            return (
              <button
                key={mode}
                type="button"
                onClick={() => setAnnual(mode === "annual")}
                className={cn(
                  "rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
                  active ? "gold-gradient text-black" : "text-muted hover:text-ink",
                )}
              >
                {mode === "annual" ? `Annual · save ${ANNUAL_DISCOUNT_PCT}%` : "Monthly"}
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {PLAN_ORDER.map((key) => {
          const plan = PLANS[key];
          const isPro = plan.tier === "pro";
          const isElite = plan.tier === "elite";
          const isFree = plan.tier === "free";
          const isCurrent = tier === plan.tier;
          const isExistingSubscriber = tier !== "free";
          const trial = isElite && ELITE_TRIAL_DAYS > 0;

          return (
            <div
              key={plan.tier}
              className={cn(
                "relative flex flex-col rounded-card p-6",
                isPro
                  ? "border border-gold/60 bg-surface shadow-[0_0_40px_-12px_rgba(212,175,55,0.4)]"
                  : "card-border",
              )}
            >
              <Badge
                variant={isPro ? "gold" : isElite ? "success" : "muted"}
                className="absolute -top-3 left-1/2 -translate-x-1/2"
              >
                {plan.badge}
              </Badge>

              <div className="flex items-center gap-2">
                <h2 className="font-display text-xl font-bold text-ink">{plan.name}</h2>
                {!isFree ? <Crown className="h-4 w-4 text-gold" aria-hidden /> : null}
              </div>

              <p className="mt-2 min-h-[40px] text-sm text-muted">{plan.blurb}</p>

              {plan.monthly > 0 ? (
                <div className="mt-4">
                  {annual ? (
                    <>
                      {/* Annual: the discounted per-month price is the headline,
                          with the monthly price struck through as the anchor. */}
                      <p className="flex items-baseline gap-1">
                        <span className="tabular font-display text-4xl font-bold text-ink">
                          {gbp(plan.perMonth)}
                        </span>
                        <span className="text-sm text-muted">/mo</span>
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
                        <s className="tabular text-muted">{gbp(plan.monthly)}/mo</s>
                        <span className="tabular font-semibold text-ink">{gbp(plan.annual)}/yr</span>
                        <span className="font-medium text-success">Save {ANNUAL_DISCOUNT_PCT}%</span>
                      </div>
                      <p className="mt-1 text-xs text-muted">
                        billed {gbp(plan.annual)}/yr
                      </p>
                    </>
                  ) : (
                    <>
                      {/* Monthly: straight monthly price, no annual savings line. */}
                      <p className="flex items-baseline gap-1">
                        <span className="tabular font-display text-4xl font-bold text-ink">
                          {gbp(plan.monthly)}
                        </span>
                        <span className="text-sm text-muted">/mo</span>
                      </p>
                      <p className="mt-1 text-xs text-muted">billed monthly</p>
                    </>
                  )}

                  {trial ? (
                    <p className="mt-1 flex items-center gap-1 text-xs font-medium text-gold">
                      <Zap className="h-3.5 w-3.5" aria-hidden />
                      {ELITE_TRIAL_DAYS}-day free trial · card required
                    </p>
                  ) : null}
                </div>
              ) : (
                <div className="mt-4">
                  <p className="flex items-baseline gap-1">
                    <span className="tabular font-display text-4xl font-bold text-ink">£0</span>
                    <span className="text-sm text-muted">/mo</span>
                  </p>
                  <p className="mt-1 text-xs text-muted">Free forever. No card required.</p>
                </div>
              )}

              <ul className="mt-5 flex-1 space-y-2">
                {(plan.features as readonly string[]).map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-ink">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-gold" aria-hidden />
                    {f}
                  </li>
                ))}
              </ul>

              <Button
                onClick={() => handleSelect(key)}
                variant={isPro ? "primary" : "secondary"}
                fullWidth
                className="mt-6"
                disabled={isCurrent || busy !== null}
                loading={busy === plan.tier}
              >
                {isCurrent
                  ? "Current plan"
                  : isFree
                    ? "Start free"
                    : isExistingSubscriber
                      ? `Switch to ${plan.name}`
                      : trial && !annual
                        ? `Start ${ELITE_TRIAL_DAYS}-day free trial`
                        : `Start ${plan.name}`}
              </Button>
            </div>
          );
        })}
      </div>

      <div className="mt-8 flex flex-col items-center gap-2 rounded-card card-border p-6 text-center">
        <ShieldCheck className="h-6 w-6 text-gold" aria-hidden />
        <p className="text-sm font-medium text-ink">Cancel anytime.</p>
        <p className="text-xs text-muted">
          Don't lose your progress — your streak, history, and plan sync across devices.
          Free starts with no card. Paid plans require a card to begin.
        </p>
      </div>

    </div>
  );
}
