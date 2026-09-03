import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal } from "@/components/landing/Reveal";

export function CTA() {
  return (
    <section className="px-4 py-20 md:py-28">
      <Reveal className="mx-auto max-w-5xl">
        <div className="glow-gold card-border relative overflow-hidden rounded-card p-10 text-center md:p-16">
          <div className="hero-glow pointer-events-none absolute inset-0" aria-hidden />
          <div className="grid-bg mask-fade-b pointer-events-none absolute inset-0 opacity-50" aria-hidden />
          <div className="relative">
            <h2 className="font-display text-3xl font-bold md:text-5xl">
              Your glow-up starts with a{" "}
              <span className="text-gold-gradient text-glow">number</span>.
            </h2>
            <p className="mx-auto mt-4 max-w-lg text-muted">
              Upload one photo. Get your baseline score and a 90-day plan to raise it.
            </p>
            <Link
              href="/signup"
              className="gold-gradient btn-glow mt-8 inline-flex h-[52px] items-center gap-2 rounded-full px-8 text-base font-semibold text-black hover:opacity-90"
            >
              See your score — free <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
            <p className="mt-4 text-xs text-muted">Free · Private · No card required</p>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
