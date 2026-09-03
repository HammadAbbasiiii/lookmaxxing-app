import { Star } from "lucide-react";
import { Reveal } from "@/components/landing/Reveal";

const TESTIMONIALS = [
  {
    quote:
      "The score called out my skin first — the 90-day plan got me on a routine that actually worked. Rescanned 30 days later and went up 6 points.",
    name: "Marcus T.",
    plan: "Pro member",
  },
  {
    quote:
      "Finally something that shows the why behind the number. The jawline and eye breakdown is exactly what I wanted to know.",
    name: "Devon R.",
    plan: "Free member",
  },
  {
    quote:
      "I was skeptical, but the 2-minute daily tasks were easy to stick to. The streak kept me honest. +9 in 90 days.",
    name: "Ali K.",
    plan: "Elite member",
  },
];

export function Testimonials() {
  return (
    <section className="border-y border-border-soft bg-surface/30 py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-4">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">Results</p>
          <h2 className="mt-3 font-display text-3xl font-bold md:text-4xl">
            Members are seeing the change
          </h2>
        </Reveal>

        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {TESTIMONIALS.map((t, i) => (
            <Reveal key={t.name} delay={i * 0.08}>
              <figure className="card-border card-hover flex h-full flex-col rounded-card p-6">
                <div className="flex gap-0.5" aria-hidden>
                  {Array.from({ length: 5 }).map((_, j) => (
                    <Star key={j} className="h-4 w-4 fill-gold text-gold" />
                  ))}
                </div>
                <blockquote className="mt-4 flex-1 text-sm leading-relaxed text-ink">
                  “{t.quote}”
                </blockquote>
                <figcaption className="mt-5 flex items-center gap-3 border-t border-border-soft pt-4">
                  <span className="flex h-9 w-9 items-center justify-center rounded-full bg-surface-2 text-sm font-semibold text-gold">
                    {t.name.charAt(0)}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-ink">{t.name}</p>
                    <p className="text-xs text-muted">{t.plan}</p>
                  </div>
                </figcaption>
              </figure>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
