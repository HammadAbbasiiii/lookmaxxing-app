import type { ReactNode } from "react";

/**
 * Route arrival (§2.3) — a screen settles in instead of hard-swapping.
 *
 * Next re-renders a `template.tsx` for every navigation inside its segment, so
 * this is the one place a transition can live without wrapping (and without
 * disabling) any real screen: the nav shell, the drawers and the scroll
 * position are all untouched — only the page body arrives.
 *
 * The animation is CSS-only and 260ms with `backwards` fill: it costs no JS,
 * cannot delay a tap, leaves no `transform` behind (a lingering transform would
 * turn this div into a containing block for any `position: fixed` child and
 * would never satisfy Playwright's stability check), and is fully disabled
 * under `prefers-reduced-motion`.
 */
export default function AppTemplate({ children }: { children: ReactNode }) {
  return <div className="screen-in">{children}</div>;
}
