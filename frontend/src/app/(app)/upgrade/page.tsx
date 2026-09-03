"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Crown, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { useMe } from "@/hooks/useMe";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { ANNUAL_DISCOUNT_PCT, PLANS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { track } from "@/lib/api/analytics";
import { createCheckout, testUpgrade } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";

const FEATURES: Record<string, string[]> = {
  free: ["1 analysis", "Baseline score", "Streak tracking"],
  pro: ["Unlimited analyses", "Full 90-day plan", "Daily check-ins", "Product recommendations"],
  elite: ["Everything in Pro", "1:1 coach Q&A", "Priority support"],
};

export default function UpgradePage() {
  const [annual, setAnnual] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const router = useRouter();
  const { data: user } = useMe();
  const tier = user?.subscription_tier ?? "free";

  function price(monthly: number): string {
    if (monthly === 0) return "$0";
    const effective = annual ? monthly * (1 - ANNUAL_DISCOUNT_PCT / 100) : monthly;
    return `$${effective.toFixed(2)}`;
  }

  function waitlistMessage(name: string, email?: string): string {
    return `You're on the ${name} waitlist — we'll email ${email || "you"} when it launches.`;
  }

  const canTest = process.env.NEXT_PUBLIC_ENABLE_TEST_PAYMENTS === "1";

  async function runTestUpgrade(target: "pro" | "elite") {
    setBusy(target);
    try {
      const res = await testUpgrade(target);
      if (res.success) {
        toast.success(`Switched to ${res.tier === "elite" ? "Elite" : "Pro"} (dev preview).`);
        window.location.href = "/dashboard";
      } else {
        toast.error("Test upgrades are disabled on this environment.");
      }
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Couldn't run test upgrade.");
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
        {(Object.keys(PLANS) as (keyof typeof PLANS)[]).map((key) => {
          const plan = PLANS[key];
          const isPro = plan.tier === "pro";
          const isCurrent = tier === plan.tier;
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
              {isPro ? (
                <Badge variant="gold" className="absolute -top-3 left-1/2 -translate-x-1/2">
                  Most popular
                </Badge>
              ) : null}

              <div className="flex items-center gap-2">
                <h2 className="font-display text-xl font-bold text-ink">{plan.name}</h2>
                {plan.tier !== "free" ? <Crown className="h-4 w-4 text-gold" aria-hidden /> : null}
              </div>

              <p className="mt-2 min-h-[40px] text-sm text-muted">{plan.blurb}</p>

              <p className="mt-4">
                <span className="tabular font-display text-4xl font-bold text-ink">
                  {price(plan.monthly)}
                </span>
                {plan.monthly > 0 ? (
                  <span className="text-sm text-muted">{annual ? "/mo" : "/mo"}</span>
                ) : null}
              </p>
              {annual && plan.monthly > 0 ? (
                <p className="mt-1 text-xs text-muted">billed annually</p>
              ) : null}

              <ul className="mt-5 flex-1 space-y-2">
                {FEATURES[plan.tier].map((f) => (
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
                  : plan.tier === "free"
                    ? "Continue free"
                    : `Start ${plan.name}`}
              </Button>
            </div>
          );
        })}
      </div>

      <div className="mt-8 flex flex-col items-center gap-2 rounded-card card-border p-6 text-center">
        <ShieldCheck className="h-6 w-6 text-gold" aria-hidden />
        <p className="text-sm font-medium text-ink">Cancel anytime. No card required to start.</p>
        <p className="text-xs text-muted">
          Don't lose your progress — your streak, history, and plan sync across devices.
        </p>
      </div>

      {canTest ? (
        <div className="mt-6 rounded-card card-border p-6">
          <h2 className="text-sm font-semibold text-ink">Developer preview</h2>
          <p className="mt-1 text-xs text-muted">
            Test payments are enabled on this build. Preview Pro or Elite without a real charge.
          </p>
          <div className="mt-3 flex flex-wrap gap-3">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => runTestUpgrade("pro")}
              loading={busy === "pro"}
              disabled={busy !== null}
            >
              Preview Pro
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => runTestUpgrade("elite")}
              loading={busy === "elite"}
              disabled={busy !== null}
            >
              Preview Elite
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
