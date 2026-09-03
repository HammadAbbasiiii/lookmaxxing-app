"use client";

import Link from "next/link";
import { ArrowRight, Lock, ShieldCheck, Sparkles, Star } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { ScoreRing } from "@/components/ui/ScoreRing";
import { scoreLabel } from "@/lib/constants";

const TRUST_CHIPS = ["Free", "Private", "90-day plan", "No card required"];

const FEATURE_BARS = [
  { label: "Symmetry", value: 82 },
  { label: "Skin", value: 74 },
  { label: "Jawline", value: 79 },
  { label: "Eyes", value: 76 },
];

function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted">{label}</span>
        <span className="tabular font-semibold text-ink">{value}</span>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-2">
        <div className="h-full rounded-full gold-gradient" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

/** Animated hero: headline, CTAs, social proof + floating phone mockup. */
export function Hero() {
  const reduce = useReducedMotion();
  const reveal = (delay: number) => ({
    initial: { opacity: 0, y: reduce ? 0 : 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.55, delay, ease: "easeOut" as const },
  });

  return (
    <section className="relative overflow-hidden">
      <div className="hero-glow pointer-events-none absolute inset-0" aria-hidden />
      <div className="grid-bg mask-fade-b pointer-events-none absolute inset-0 opacity-60" aria-hidden />

      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 pb-16 pt-14 md:grid-cols-[1.1fr_0.9fr] md:pb-24 md:pt-20">
        {/* Copy */}
        <div className="text-center md:text-left">
          <motion.div {...reveal(0)}>
            <span className="inline-flex items-center gap-2 rounded-full border border-gold/30 bg-gold/10 px-3.5 py-1.5 text-xs font-semibold text-gold-bright">
              <Sparkles className="h-3.5 w-3.5" aria-hidden />
              AI face analysis + 90-day plan
            </span>
          </motion.div>

          <motion.h1
            {...reveal(0.08)}
            className="mt-6 font-display text-5xl font-bold leading-[1.02] tracking-tight md:text-7xl"
          >
            What&apos;s your{" "}
            <span className="text-gold-gradient text-glow">score</span>?
          </motion.h1>

          <motion.p
            {...reveal(0.16)}
            className="mx-auto mt-5 max-w-xl text-base text-muted md:mx-0 md:text-lg"
          >
            Upload one photo. Get a feature-by-feature breakdown — symmetry, skin,
            jawline, and eyes — then follow a personalised 90-day plan to raise it.
          </motion.p>

          <motion.div
            {...reveal(0.24)}
            className="mt-8 flex flex-col items-center gap-3 sm:flex-row md:justify-start"
          >
            <Link
              href="/signup"
              className="gold-gradient btn-glow inline-flex h-[52px] items-center gap-2 rounded-full px-8 text-base font-semibold text-black hover:opacity-90"
            >
              See your score — free <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex h-[52px] items-center gap-2 rounded-full border border-border-soft bg-surface/60 px-8 text-base font-medium text-ink backdrop-blur transition-colors hover:border-gold/40 hover:text-gold-bright"
            >
              How it works
            </a>
          </motion.div>

          <motion.div
            {...reveal(0.32)}
            className="mt-6 flex flex-wrap items-center justify-center gap-2 md:justify-start"
          >
            {TRUST_CHIPS.map((chip) => (
              <span
                key={chip}
                className="inline-flex items-center gap-1.5 rounded-full border border-border-soft bg-surface/60 px-3 py-1 text-xs text-muted backdrop-blur"
              >
                <ShieldCheck className="h-3.5 w-3.5 text-gold" aria-hidden />
                {chip}
              </span>
            ))}
          </motion.div>

          <motion.div
            {...reveal(0.4)}
            className="mt-6 flex items-center justify-center gap-2 text-sm text-muted md:justify-start"
          >
            <span className="flex" aria-hidden>
              {Array.from({ length: 5 }).map((_, i) => (
                <Star key={i} className="h-4 w-4 fill-gold text-gold" />
              ))}
            </span>
            <span>Loved by the looksmaxxing community</span>
          </motion.div>
        </div>

        {/* Phone mockup */}
        <motion.div
          initial={{ opacity: 0, y: reduce ? 0 : 32, scale: reduce ? 1 : 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.7, delay: 0.2, ease: "easeOut" }}
          className="relative mx-auto w-full max-w-[340px]"
        >
          <div className="animate-float relative rounded-[2.5rem] border border-border-soft bg-surface/80 p-3 shadow-[0_40px_90px_-30px_rgba(0,0,0,0.9)] backdrop-blur">
            <div className="glow-gold rounded-[2rem] border border-gold/20 bg-background p-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted">Your score</p>
                  <p className="text-sm font-semibold text-ink">Elite symmetry</p>
                </div>
                <span className="rounded-full bg-gold/15 px-2.5 py-1 text-xs font-semibold text-gold-bright">
                  +13 potential
                </span>
              </div>

              <div className="mt-4 flex justify-center">
                <ScoreRing score={84} size={150} label={scoreLabel(84)} />
              </div>

              <div className="mt-5 space-y-3">
                {FEATURE_BARS.map((b) => (
                  <Bar key={b.label} {...b} />
                ))}
              </div>

              <div className="mt-5 flex items-center gap-3 rounded-xl border border-border-soft bg-surface-2 p-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-full gold-gradient text-sm font-bold text-black">
                  2m
                </span>
                <div>
                  <p className="text-xs font-semibold text-ink">Today&apos;s task</p>
                  <p className="text-xs text-muted">Jawline exercises · 2 min</p>
                </div>
                <Lock className="ml-auto h-4 w-4 text-muted" aria-hidden />
              </div>
            </div>
          </div>

          <div className="absolute -left-6 top-10 hidden animate-float-slow rounded-xl border border-border-soft bg-surface px-3 py-2 text-xs font-medium text-ink shadow-lg sm:block">
            🗿 Jawline 79
          </div>
          <div className="absolute -right-4 bottom-16 hidden animate-float rounded-xl border border-border-soft bg-surface px-3 py-2 text-xs font-medium text-ink shadow-lg sm:block">
            ✨ Skin 74
          </div>
        </motion.div>
      </div>
    </section>
  );
}
