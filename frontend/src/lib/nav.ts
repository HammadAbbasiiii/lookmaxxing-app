export const GLOW_LINKS = [
  { href: "/glow", label: "Daily" },
  { href: "/glow-up", label: "Insights" },
  { href: "/glowups", label: "Social" },
  { href: "/arc", label: "Journey" },
  { href: "/peak-you", label: "Simulator" },
];

/** Exact-or-child match so `/glow` doesn't light up on `/glow-up`/`/glowups`. */
export function isActivePath(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** True when on any page in the "Glow" section (daily reveal + sub-features). */
export function isGlowPath(pathname: string): boolean {
  return GLOW_LINKS.some((l) => isActivePath(pathname, l.href));
}
