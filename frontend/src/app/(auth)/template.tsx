import type { ReactNode } from "react";

/**
 * Auth route arrival (§2.3) — same law as the app shell, applied to
 * login/signup/reset. Signing in is the first impression the product gets to
 * make, so the form settles in rather than snapping; it is the same 260ms
 * CSS-only, transform-free, reduced-motion-aware entrance as `(app)/template.tsx`.
 */
export default function AuthTemplate({ children }: { children: ReactNode }) {
  return <div className="screen-in">{children}</div>;
}
