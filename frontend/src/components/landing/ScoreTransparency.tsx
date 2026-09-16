import { ScanFace, ShieldCheck, SunMedium } from "lucide-react";
import { Reveal } from "@/components/landing/Reveal";

/**
 * Replaces the old fabricated-testimonial section.
 *
 * We have no customer quotes to show yet, so we show something we can actually
 * stand behind: how the number is produced and what it can't tell you. Every
 * claim here mirrors the real pipeline (landmarks -> symmetry/skin/jawline/eyes
 * -> weighted overall -> 90-day plan).
 */
const PILLARS = [
  {
    icon: ScanFace,
    title: "One photo, four measurements",
    text: "We detect your facial landmarks, then score symmetry, skin, jawline and eyes. Your overall score is a weighted blend of those — not a single hidden number.",
  },
  {
    icon: SunMedium,
    title: "Your lighting moves your score",
    text: "Angle, lighting and lens all shift the result. Shoot the same way each time so your progress chart measures you, not your camera.",
  },
  {
    icon: ShieldCheck,
    title: "An estimate, not a verdict",
    text: "This is an AI estimate from a single photo. It isn't medical, dermatological or psychological advice — and it is never a measure of your worth.",
  },
];

export function ScoreTransparency() {
  return (
    <section className="border-y border-border-soft bg-surface/30 py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-4">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">
            Radical honesty
          </p>
          <h2 className="mt-3 font-display text-3xl font-bold md:text-4xl">
            How your score is built
          </h2>
          <p className="mt-3 text-muted">
            No black box. Here&apos;s exactly what goes into your number — and what it
            can&apos;t tell you.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {PILLARS.map((p, i) => {
            const Icon = p.icon;
            return (
              <Reveal key={p.title} delay={i * 0.08}>
                <div className="card-border card-hover h-full rounded-card p-6">
                  <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gold/15 text-gold">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <h3 className="mt-4 text-lg font-semibold text-ink">{p.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{p.text}</p>
                </div>
              </Reveal>
            );
          })}
        </div>

        <Reveal delay={0.24}>
          <p className="mx-auto mt-10 max-w-2xl text-center text-sm text-muted">
            Use one score as a baseline, then track change over time. Progress is the
            point — not the number.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
