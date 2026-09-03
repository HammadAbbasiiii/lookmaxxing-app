import { Plus } from "lucide-react";
import { Reveal } from "@/components/landing/Reveal";

const FAQS = [
  {
    q: "Is it really free?",
    a: "Yes. Your first analysis and baseline score are free. Pro unlocks unlimited analyses and the full 90-day plan.",
  },
  {
    q: "How accurate is the score?",
    a: "It's an AI estimate from one photo — best used as a baseline to track change, not a definitive measure of worth. Use clean lighting and a straight-on selfie for the best result.",
  },
  {
    q: "What happens to my photos?",
    a: "Private by default. Photos are encrypted in transit, never shared, and can be deleted anytime — including from our image provider.",
  },
  {
    q: "Do I need to pay to see my score?",
    a: "No. Your baseline score is free. Paid tiers add unlimited analyses, the full plan, daily check-ins, and coaching.",
  },
  {
    q: "What does the 90-day plan include?",
    a: "Three phases (Foundation, Building, Mastery) with daily 2-minute tasks, milestones, and streak tracking.",
  },
  {
    q: "Which features does it analyze?",
    a: "Symmetry, skin quality, jawline, eye area, face shape, and overall harmony — each scored separately.",
  },
  {
    q: "Can I track my progress?",
    a: "Yes. Rescan anytime to log a new check-in and watch your score change over time.",
  },
  {
    q: "How is this different from other looksmaxxing apps?",
    a: "We focus on the plan, not just the number. A score is useless without action — so we build a 90-day routine around yours.",
  },
];

export function FAQ() {
  return (
    <section id="faq" className="scroll-mt-24 py-20 md:py-28">
      <div className="mx-auto max-w-3xl px-4">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">FAQ</p>
          <h2 className="mt-3 font-display text-3xl font-bold md:text-4xl">Questions, answered</h2>
        </Reveal>

        <div className="mt-10 space-y-3">
          {FAQS.map((item, i) => (
            <Reveal key={item.q} delay={i * 0.04}>
              <details className="group card-border rounded-card">
                <summary className="flex cursor-pointer items-center justify-between gap-4 p-5">
                  <span className="font-medium text-ink">{item.q}</span>
                  <Plus
                    className="h-5 w-5 shrink-0 text-gold transition-transform duration-200 group-open:rotate-45"
                    aria-hidden
                  />
                </summary>
                <p className="px-5 pb-5 text-sm leading-relaxed text-muted">{item.a}</p>
              </details>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
