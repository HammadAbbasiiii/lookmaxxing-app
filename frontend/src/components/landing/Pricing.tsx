"use client";

import Link from "next/link";
import { useState } from "react";
import { Check, Crown } from "lucide-react";
import { Reveal } from "@/components/landing/Reveal";
import { ANNUAL_DISCOUNT_PCT, PLANS } from "@/lib/constants";
import { cn } from "@/lib/utils";

const FEATURES: Record<string, string[]> = {
  free: ["1 analysis", "Baseline score", "Streak tracking"],
  pro: ["Unlimited analyses", "Full 90-day plan", "Daily check-ins", "Product recommendations"],
  elite: ["Everything in Pro", "1:1 coach Q&A", "Priority support"],
};

export function Pricing() {
  const [annual, setAnnual] = useState(true);

  function price(monthly: number): string {
    if (monthly === 0) return "$0";
    const effective = annual ? monthly * (1 - ANNUAL_DISCOUNT_PCT / 100) : monthly;
    return `$${effective.toFixed(2)}`;
  }

  return (
    <section id="pricing" className="scroll-mt-24 py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-4">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">Pricing</p>
          <h2 className="mt-3 font-display text-3xl font-bold md:text-4xl">
            Start free. Upgrade when you&apos;re ready.
          </h2>
          <p className="mt-3 text-muted">
            Your baseline score is always free. Paid tiers unlock the full plan and coaching.
          </p>
        </Reveal>

        <Reveal delay={0.05} className="mb-10 mt-8 flex justify-center">
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
        </Reveal>

        <div className="grid gap-5 md:grid-cols-3">
          {(Object.keys(PLANS) as (keyof typeof PLANS)[]).map((key, i) => {
            const plan = PLANS[key];
            const isPro = plan.tier === "pro";
            return (
              <Reveal key={plan.tier} delay={i * 0.07}>
                <div
                  className={cn(
                    "relative flex h-full flex-col rounded-card p-6",
                    isPro ? "glow-gold border border-gold/60 bg-surface" : "card-border",
                  )}
                >
                  {isPro ? (
                    <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full gold-gradient px-3 py-1 text-xs font-bold text-black">
                      Most popular
                    </span>
                  ) : null}

                  <div className="flex items-center gap-2">
                    <h3 className="font-display text-xl font-bold text-ink">{plan.name}</h3>
                    {plan.tier !== "free" ? <Crown className="h-4 w-4 text-gold" aria-hidden /> : null}
                  </div>

                  <p className="mt-2 min-h-[40px] text-sm text-muted">{plan.blurb}</p>

                  <p className="mt-4">
                    <span className="tabular font-display text-4xl font-bold text-ink">
                      {price(plan.monthly)}
                    </span>
                    {plan.monthly > 0 ? <span className="text-sm text-muted">/mo</span> : null}
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

                  <Link
                    href="/signup"
                    className={cn(
                      "mt-6 inline-flex h-11 items-center justify-center gap-2 rounded-xl text-sm font-semibold transition-all active:scale-[0.98]",
                      isPro
                        ? "gold-gradient btn-glow text-black hover:opacity-90"
                        : "border border-border-soft bg-surface text-ink hover:bg-surface-2",
                    )}
                  >
                    {plan.tier === "free" ? "Start free" : `Start ${plan.name}`}
                  </Link>
                </div>
              </Reveal>
            );
          })}
        </div>

        <Reveal delay={0.1}>
          <p className="mt-8 text-center text-xs text-muted">
            Cancel anytime. No card required to start.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
