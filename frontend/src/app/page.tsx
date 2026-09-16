import { LandingNav } from "@/components/landing/LandingNav";
import { Hero } from "@/components/landing/Hero";
import { StatsBar } from "@/components/landing/StatsBar";
import { Features } from "@/components/landing/Features";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { ReportBreakdown } from "@/components/landing/ReportBreakdown";
import { ScoreTransparency } from "@/components/landing/ScoreTransparency";
import { Pricing } from "@/components/landing/Pricing";
import { FAQ } from "@/components/landing/FAQ";
import { CTA } from "@/components/landing/CTA";
import { Footer } from "@/components/landing/Footer";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-ink">
      <LandingNav />
      <main>
        <Hero />
        <StatsBar />
        <Features />
        <HowItWorks />
        <ReportBreakdown />
        <ScoreTransparency />
        <Pricing />
        <FAQ />
        <CTA />
      </main>
      <Footer />
    </div>
  );
}
