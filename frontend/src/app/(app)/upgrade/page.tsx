"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, Crown, Flame, ShieldCheck, Zap } from "lucide-react";
import { toast } from "sonner";
import { useMe } from "@/hooks/useMe";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { ANNUAL_DISCOUNT_PCT, ELITE_TRIAL_DAYS, PLAN_ORDER, PLANS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { track } from "@/lib/api/analytics";
import { changePlan, createCheckout, getOffer } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { normalizeTier, tierLabel } from "@/lib/tiers";

export default function UpgradePage() {
  const [annual, setAnnual] = useState(true);
  // Flipped once the visitor picks a view themselves: the eligibility default
  // below must never yank the toggle out from under them.
  const [pricingTouched, setPricingTouched] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const router = useRouter();
  const qc = useQueryClient();
  const { data: user } = useMe();
  const tier = user?.subscription_tier ?? "free";

  // DEF-015: the £1 first month is server-authoritative. `/payments/offer` reads
  // the live Stripe price + coupon, so the page can never advertise a discount
  // the checkout wouldn't honour (that mismatch — £1 charged, £9.99 shown — is
  // the trust bug this replaced). If the call fails we simply show list pricing.
  const offer = useQuery({
    queryKey: ["offer"],
    queryFn: getOffer,
    enabled: tier === "free",
    staleTime: 60_000,
  });
  const offerData = offer.data;
  const offerEligible = offerData?.eligible === true;
  const offerUsed = offerData?.reason === "used";
  const firstMonthAmount = offerData?.first_month_amount ?? null;
  const regularAmount = offerData?.regular_amount ?? PLANS.pro.monthly;

  // DEF-017: the £1 offer is only advertised when Stripe confirmed it. On
  // `verified: false` (the coupon/price couldn't be read — e.g. the coupon was
  // never created in the live Stripe mode) the page says the offer is
  // unavailable and checkout runs at list price: printing £1 and charging £9.99
  // is the DEF-015 trust bug, and an unverified offer is never shown as a price.
  const offerVerified = offerData?.verified === true;
  const offerAvailable = offerEligible && offerVerified && firstMonthAmount != null;
  const offerUnavailable = offerEligible && !offerVerified;
  // Names the offer even when the server sent no amount (eligible, but the coupon
  // couldn't be read): the launch configuration in config.py is £9.99 with £8.99
  // off, so £1 is the documented figure this deployment is meant to honour.
  const offerAmount = firstMonthAmount ?? 1;

  // The coupon is `duration=once` on the Pro *monthly* price, so a £1 first month
  // only exists in the monthly view. Leaving the annual default in place hid it
  // behind a small link: a brand-new member landed on £4.20/mo (list £9.99, struck)
  // with a "Start Pro" button and concluded the launch offer was missing. Land an
  // eligible visitor on the price they can actually buy it at.
  const offerPending = offer.isLoading && tier === "free";
  useEffect(() => {
    if (offerEligible && !pricingTouched) setAnnual(false);
  }, [offerEligible, pricingTouched]);

  function gbp(amount: number): string {
    return `£${amount.toFixed(2)}`;
  }

  function waitlistMessage(name: string, email?: string): string {
    return `You're on the ${name} waitlist — we'll email ${email || "you"} when it launches.`;
  }

  async function handleSelect(
    planKey: keyof typeof PLANS,
    opts: { firstMonthOffer?: boolean; annual?: boolean } = {},
  ) {
    const plan = PLANS[planKey];
    if (plan.tier === "free") {
      router.push("/dashboard");
      return;
    }
    const firstMonthOffer = Boolean(opts.firstMonthOffer);
    // The banner's CTA buys the *monthly* plan — the coupon is `duration=once` on
    // the Pro monthly price — so it must not inherit a toggle left on annual.
    const annualView = opts.annual ?? annual;
    track("upgrade_click", {
      metadata: {
        tier: plan.tier,
        plan: plan.name,
        ...(firstMonthOffer ? { first_month_offer: true } : {}),
      },
    });
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

      const res = await createCheckout(plan.tier as "pro" | "elite", annualView, firstMonthOffer);
      if (res.checkout_url) {
        if (firstMonthOffer && res.offer_applied === false) {
          // Stripe refused the coupon (deleted/expired, or missing in this Stripe
          // mode) and the session fell back to list price. We're about to leave
          // the page, so log it instead of toasting into a page we no longer own.
          console.warn(
            "[upgrade] first-month coupon was not applied — checkout continues at list price",
          );
        }
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

  /**
   * The banner's CTA. Pins the *monthly* Pro checkout (the coupon is
   * `duration=once` on the Pro monthly price) and moves the toggle to match, so
   * the cards below can never contradict what the banner just sold.
   */
  async function handleFirstMonthOffer() {
    setPricingTouched(true);
    setAnnual(false);
    await handleSelect("pro", { firstMonthOffer: true, annual: false });
  }

  return (
    <div className="mx-auto max-w-4xl">
      <ScreenHeader
        title="Upgrade"
        subtitle={
          tier !== "free"
            ? "You're already on " + tierLabel(normalizeTier(tier)) + "."
            : "Keep your streak & history synced. Cancel anytime."
        }
      />

      {/* DEF-017: the launch offer now gets the top of the page — full-width, with
          its own CTA — instead of a line inside a £9.99 price card, where a
          brand-new visitor read it as a footnote and concluded the offer was
          missing. This does not reintroduce the DEF-015 mismatch: the banner is
          the *only* place the £1 is claimed, it prints the follow-on price right
          beside it, it renders solely for an offer Stripe has verified
          (`verified: true`), and every card below stays at list price. */}
      {offerAvailable ? (
        <section
          aria-labelledby="first-month-offer-title"
          className="animate-banner-in mb-6 overflow-hidden rounded-card border border-gold/60 bg-gradient-to-r from-gold/25 via-gold/10 to-transparent p-5 shadow-[0_0_44px_-14px_rgba(212,175,55,0.55)] sm:p-6"
        >
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
            <div className="min-w-0">
              <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-gold">
                <Flame className="h-4 w-4 animate-pulse-glow" aria-hidden />
                First month special
              </p>
              <h2
                id="first-month-offer-title"
                className="mt-1 font-display text-2xl font-bold text-ink"
              >
                Get started for {gbp(firstMonthAmount)}
              </h2>
              <p className="mt-1 text-sm text-muted">
                Your first month is just {gbp(firstMonthAmount)}, then{" "}
                <span className="font-medium text-ink">{gbp(regularAmount)}/month</span> from month
                2. Cancel anytime.
              </p>
            </div>
            <span className="animate-cta-pulse inline-block w-full shrink-0 sm:w-auto">
              <Button
                onClick={handleFirstMonthOffer}
                size="lg"
                className="w-full hover:shadow-[0_0_28px_-6px_rgba(212,175,55,0.75)] sm:w-auto"
                disabled={busy !== null}
                loading={busy === "pro"}
              >
                Start for {gbp(firstMonthAmount)}
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Button>
            </span>
          </div>
        </section>
      ) : offerUnavailable ? (
        /* Eligible, but Stripe couldn't confirm the coupon — the classic "the
           offer exists in test mode only" case. Say so; never fake the price. */
        <p
          role="status"
          className="mb-6 rounded-card border border-border-soft bg-surface-2 p-4 text-sm text-muted"
        >
          The {gbp(offerAmount)} first-month offer is temporarily unavailable — the plans below
          are at their regular price.
        </p>
      ) : offerPending ? (
        /* Same slot, reserved: without it the offer pops in and shoves the cards
           down the moment the visitor starts reading them. */
        <p
          role="status"
          className="mb-6 rounded-card border border-border-soft bg-surface-2 p-4 text-sm text-muted"
        >
          Checking your offer…
        </p>
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
                onClick={() => {
                  setPricingTouched(true);
                  setAnnual(mode === "annual");
                }}
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
        {PLAN_ORDER.map((key, index) => {
          const plan = PLANS[key];
          const isPro = plan.tier === "pro";
          const isElite = plan.tier === "elite";
          const isFree = plan.tier === "free";
          const isCurrent = tier === plan.tier;
          const isExistingSubscriber = tier !== "free";
          const trial = isElite && ELITE_TRIAL_DAYS > 0;
          // DEF-017: the £1 first month is sold by the banner above, not by this
          // card. The card keeps its list price and only its CTA states the offer
          // amount — and only in the monthly view, because annual can't carry a
          // `duration=once` coupon and a button promising £1 there would lie.
          const proOfferCta = isPro && offerAvailable && firstMonthAmount != null;

          return (
            <div
              key={plan.tier}
              className={cn(
                // Staggered entrance (0.1s per card) + lift on hover. The
                // animation uses `backwards` fill so the transform it finishes on
                // is released and `hover:-translate-y-1` still works.
                "animate-card-in relative flex flex-col rounded-card p-6 transition-all duration-200 hover:-translate-y-1",
                isPro
                  ? "border border-gold/60 bg-surface shadow-[0_0_40px_-12px_rgba(212,175,55,0.4)] hover:shadow-[0_0_52px_-10px_rgba(212,175,55,0.55)]"
                  : "card-border hover:shadow-[0_10px_30px_-16px_rgba(0,0,0,0.8)]",
              )}
              style={{ animationDelay: `${index * 100}ms` }}
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
                      {/* Monthly list price. The £1 first month is the banner's job
                          (DEF-017); keeping it off the price block is what makes
                          this number the regular, always-true number. */}
                      <p className="flex items-baseline gap-1">
                        <span className="tabular font-display text-4xl font-bold text-ink">
                          {gbp(plan.monthly)}
                        </span>
                        <span className="text-sm text-muted">/mo</span>
                      </p>
                      <p className="mt-1 text-xs text-muted">billed monthly</p>
                    </>
                  )}

                  {/* DEF-017: this view used to carry its own "switch to monthly
                      for a £1 first month" button, because the offer was otherwise
                      invisible from the annual view. The banner above is visible in
                      every view and states the £1 outright — which is exactly what
                      that button was compensating for — so the card stays a price
                      card. */}
                  {isPro && offerUsed ? (
                    <p className="mt-1 text-xs text-muted">
                      Your £1 first month has already been used.
                    </p>
                  ) : null}

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
                onClick={() =>
                  handleSelect(key, { firstMonthOffer: proOfferCta && !annual })
                }
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
                    : proOfferCta && !annual
                      ? `Start for ${gbp(firstMonthAmount)}`
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
