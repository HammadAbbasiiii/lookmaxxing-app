import {
  CalendarDays,
  Lock,
  ScanFace,
  ShoppingBag,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { Reveal } from "@/components/landing/Reveal";

const FEATURES = [
  {
    icon: ScanFace,
    title: "Face analysis",
    text: "Symmetry, proportions, jawline, cheekbones, eye area, and face shape — scored from a single photo.",
  },
  {
    icon: Sparkles,
    title: "Skin score",
    text: "Texture, clarity, and tone feedback so you know exactly what to treat first.",
  },
  {
    icon: CalendarDays,
    title: "90-day plan",
    text: "Three phases — Foundation, Building, Mastery — with 2-minute daily tasks and milestones.",
  },
  {
    icon: TrendingUp,
    title: "Progress & streaks",
    text: "Check in with new photos, keep your streak alive, and watch your score climb over time.",
  },
  {
    icon: ShoppingBag,
    title: "Product picks",
    text: "Curated grooming and skincare recommendations matched to your goals and budget.",
  },
  {
    icon: Lock,
    title: "Private by design",
    text: "Photos encrypted in transit, never shared, and deleted anytime — including from our provider.",
  },
];

export function Features() {
  return (
    <section id="features" className="scroll-mt-24 py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-4">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">
            Everything you need
          </p>
          <h2 className="mt-3 font-display text-3xl font-bold md:text-4xl">
            More than a number
          </h2>
          <p className="mt-3 text-muted">
            A score is just the start. LookMaxx turns it into a plan you can
            actually follow.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => {
            const Icon = f.icon;
            return (
              <Reveal key={f.title} delay={i * 0.06}>
                <div className="card-border card-hover rounded-card p-6">
                  <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gold/15 text-gold">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  <h3 className="mt-4 text-lg font-semibold text-ink">{f.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted">{f.text}</p>
                </div>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
