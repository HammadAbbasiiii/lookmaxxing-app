/**
 * Primary navigation — the single source of truth for the desktop top nav and
 * the mobile bottom tab bar (§7.2: five tabs). Defined once here so the two navs
 * can never drift apart, and so a surface has exactly one home.
 */
export const PRIMARY_TABS = [
  { href: "/dashboard", label: "Home" },
  { href: "/plan", label: "Plan" },
  { href: "/coach", label: "Coach" },
  { href: "/glow", label: "Glow" },
  { href: "/explore", label: "Explore" },
] as const;

/**
 * Contextual sub-tabs for the Glow section. `/glowups` (the community feed) is
 * deliberately NOT listed: it belongs to Explore, so the Glow tab stays about
 * the daily ritual instead of being a container for five unrelated surfaces.
 */
export const GLOW_LINKS = [
  { href: "/glow", label: "Daily" },
  { href: "/glow-up", label: "Insights" },
  { href: "/arc", label: "Journey" },
  { href: "/peak-you", label: "Simulator" },
] as const;

/** Exact-or-child match so `/glow` doesn't light up on `/glow-up`/`/glowups`. */
export function isActivePath(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** Minimum tier a destination needs to be *useful* (not just reachable). */
export type NavTier = "pro" | "elite";

/**
 * Destinations that are gated behind a paid tier, used to print the Pro/Elite
 * hint next to a nav item so nobody has to tap through to discover a paywall.
 *
 * What is deliberately NOT here, because the free tier still gets something real:
 *  - `/plan`   — the plan and check-ins render for everyone (see DEF-012);
 *  - `/glow`   — the daily reveal is free; only the Day-90 zero-blur is Elite;
 *  - `/arc`    — XP, level and badges are free; only claiming quests is Pro;
 *  - `/glowups`— the feed is free; only the movie is Elite (hinted on the card);
 *  - `/explore`, `/products`, `/progress` — free today (see DEF-012).
 */
export const GATED_DESTINATIONS = {
  "/coach": "pro",
  "/glow-up": "pro",
  "/peak-you": "pro",
} as const satisfies Record<string, NavTier>;

/** Tier hint for a nav destination, or undefined when it is free. */
export function navTier(href: string): NavTier | undefined {
  return (GATED_DESTINATIONS as Record<string, NavTier>)[href];
}

/** True when on any page in the "Glow" section (daily reveal + sub-features). */
export function isGlowPath(pathname: string): boolean {
  return GLOW_LINKS.some((l) => isActivePath(pathname, l.href));
}

/**
 * Whether a primary tab is active for this path. Glow is the one tab that owns
 * several routes, so it stays lit across its whole section; everything else
 * matches itself and its children.
 */
export function isTabActive(pathname: string, tabHref: string): boolean {
  if (tabHref === "/glow") return isGlowPath(pathname);
  return isActivePath(pathname, tabHref);
}

