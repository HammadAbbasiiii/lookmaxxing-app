import Link from "next/link";
import { Logo } from "@/components/layout/Logo";

const PRODUCT = [
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#report", label: "Your report" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
];

const ACCOUNT = [
  { href: "/login", label: "Log in" },
  { href: "/signup", label: "Get started" },
  { href: "mailto:support@lookmaxx.app", label: "Contact" },
];

const LEGAL = [
  { href: "/privacy", label: "Privacy" },
  { href: "/terms", label: "Terms" },
];

export function Footer() {
  return (
    <footer className="border-t border-border-soft bg-surface/30">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-14 md:grid-cols-[1.5fr_1fr_1fr_1fr]">
        <div>
          <Logo />
          <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted">
            Upload one photo. Get your baseline score and a 90-day plan to improve it.
            Free, private, and yours forever.
          </p>
        </div>

        <FooterCol title="Product" links={PRODUCT} />
        <FooterCol title="Account" links={ACCOUNT} />
        <FooterCol title="Legal" links={LEGAL} />
      </div>

      <div className="border-t border-border-soft">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-3 px-4 py-6 text-sm text-muted md:flex-row">
          <p>© {new Date().getFullYear()} LookMaxx. All rights reserved.</p>
          <p className="text-xs">Made for the looksmaxxing community.</p>
        </div>
      </div>
    </footer>
  );
}

function FooterCol({
  title,
  links,
}: {
  title: string;
  links: { href: string; label: string }[];
}) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-[0.15em] text-muted">{title}</h3>
      <ul className="mt-4 space-y-2.5">
        {links.map((l) => (
          <li key={l.label}>
            <Link href={l.href} className="text-sm text-muted transition-colors hover:text-ink">
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
