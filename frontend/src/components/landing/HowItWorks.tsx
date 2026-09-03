import { CalendarDays, Gauge, ScanFace } from "lucide-react";
import { Reveal } from "@/components/landing/Reveal";

const STEPS = [
  {
    icon: ScanFace,
    step: "01",
    title: "Upload one photo",
    text: "A clear, front-facing selfie. We compress it locally and keep it private — no social login required.",
  },
  {
    icon: Gauge,
    step: "02",
    title: "Get your baseline score",
    text: "Symmetry, skin, jawline, eyes, and potential — broken down into one number you can track over time.",
  },
  {
    icon: CalendarDays,
    step: "03",
    title: "Follow a 90-day plan",
    text: "Daily 2-minute tasks, streaks, and progress photos to turn the score into real, visible change.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="scroll-mt-24 border-y border-border-soft bg-surface/30 py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-4">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">
            How it works
          </p>
          <h2 className="mt-3 font-display text-3xl font-bold md:text-4xl">
            Three steps. Real change.
          </h2>
          <p className="mt-3 text-muted">
            From first photo to a full glow-up routine in under five minutes.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            return (
              <Reveal key={s.step} delay={i * 0.08}>
                <div className="relative h-full card-border card-hover rounded-card p-6">
                  <span className="absolute right-6 top-6 font-display text-4xl font-bold text-surface-2">
                    {s.step}
                  </span>
                  <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl gold-gradient text-black">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <h3 className="mt-4 text-lg font-semibold text-ink">{s.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{s.text}</p>
                </div>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
