import { Check, Sparkles } from "lucide-react";
import { Reveal } from "@/components/landing/Reveal";

const REPORT = [
  { label: "Face symmetry", value: 82, note: "Balanced proportions, minor asymmetry" },
  { label: "Skin quality", value: 74, note: "Clear overall, uneven tone on cheeks" },
  { label: "Jawline", value: 79, note: "Good definition, room to sharpen" },
  { label: "Eye area", value: 76, note: "Positive canthal tilt, mild dark circles" },
  { label: "Harmony", value: 81, note: "Features sit well together" },
];

const INCLUDED = [
  "Actionable next steps for every feature",
  "A 3-phase, 90-day improvement plan",
  "Milestones and streak tracking",
  "Product picks matched to your goals",
  "Rescan anytime to log a new check-in",
];

function ReportRow({ label, value, note }: { label: string; value: number; note: string }) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-ink">{label}</span>
        <span className="tabular font-display text-lg font-bold text-ink">{value}</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface-2">
        <div className="h-full rounded-full gold-gradient" style={{ width: `${value}%` }} />
      </div>
      <p className="mt-1 text-xs text-muted">{note}</p>
    </div>
  );
}

export function ReportBreakdown() {
  return (
    <section id="report" className="scroll-mt-24 py-20 md:py-28">
      <div className="mx-auto max-w-6xl px-4">
        <Reveal className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gold">Your report</p>
          <h2 className="mt-3 font-display text-3xl font-bold md:text-4xl">Every detail, decoded</h2>
          <p className="mt-3 text-muted">Your analysis goes far beyond one number. Here&apos;s what you&apos;ll see.</p>
        </Reveal>

        <div className="mt-12 grid items-center gap-10 lg:grid-cols-2">
          <Reveal>
            <div className="glow-gold card-border rounded-card p-6 md:p-8">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted">Baseline report</p>
                  <p className="font-display text-2xl font-bold text-ink">
                    Overall <span className="text-gold-gradient">84</span>
                  </p>
                </div>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-gold/15 px-3 py-1 text-xs font-semibold text-gold-bright">
                  <Sparkles className="h-3.5 w-3.5" aria-hidden />
                  Elite symmetry
                </span>
              </div>
              <div className="mt-6 space-y-5">
                {REPORT.map((r) => (
                  <ReportRow key={r.label} {...r} />
                ))}
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <h3 className="font-display text-xl font-bold text-ink md:text-2xl">You&apos;ll also get</h3>
            <ul className="mt-5 space-y-3">
              {INCLUDED.map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm text-ink md:text-base">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gold/15">
                    <Check className="h-3 w-3 text-gold" aria-hidden />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
            <p className="mt-6 text-sm text-muted">
              Use one score as a baseline, then track change over time — not a definitive measure of worth.
            </p>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
