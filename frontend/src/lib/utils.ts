// Small dependency-free utilities.

/** Join class names, dropping falsy values. */
export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

/** Clamp a number to an inclusive range. */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** Format a number as a score; null/undefined → "—". */
export function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return Math.round(value).toString();
}

/** Truncate a string to `max` chars (no mid-word surprises in messages). */
export function truncate(text: string, max = 200): string {
  if (text.length <= max) return text;
  return text.slice(0, max - 1).trimEnd() + "…";
}

/** A valid http(s) URL, or null (defensive image rendering, §9.5). */
export function safeUrl(value: unknown): string | null {
  if (typeof value !== "string" || value.length === 0) return null;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? value : null;
  } catch {
    return null;
  }
}

/** Append Cloudinary auto-format/quality transforms to any res.cloudinary.com URL. */
export function optimizedImage(url: string | null | undefined): string | null {
  const safe = safeUrl(url);
  if (!safe) return null;
  if (safe.includes("res.cloudinary.com") && !safe.includes("/upload/f_auto")) {
    return safe.replace("/upload/", "/upload/f_auto,q_auto/");
  }
  return safe;
}

/**
 * Validate the `?next=` redirect target against an allowlist of internal app
 * paths (§7.3). Prevents open-redirect attacks.
 */
const ALLOWED_NEXT_PREFIXES = [
  "/dashboard",
  "/plan",
  "/progress",
  "/explore",
  "/products",
  "/upgrade",
  "/settings",
  "/upload",
  "/analyzing",
  "/results",
  "/onboarding",
  "/coach",
  "/glow-up",
  "/peak-you",
  "/arc",
  "/glow",
  "/glowups",
];

export function safeNext(raw: string | null | undefined): string {
  if (!raw) return "/dashboard";
  if (!raw.startsWith("/")) return "/dashboard";
  // Block protocol-relative and backslash tricks.
  if (raw.startsWith("//") || raw.includes("\\")) return "/dashboard";
  const ok = ALLOWED_NEXT_PREFIXES.some(
    (p) => raw === p || raw.startsWith(p + "/"),
  );
  return ok ? raw : "/dashboard";
}

/** First name from a full name (for greeting / anonymization). */
export function firstName(name: string | null | undefined): string {
  const trimmed = (name ?? "").trim();
  if (!trimmed) return "";
  return trimmed.split(/\s+/)[0];
}

/** Capitalize the first letter of a word ("improving" → "Improving"). */
export function titleCase(word: string): string {
  if (!word) return "";
  return word.charAt(0).toUpperCase() + word.slice(1);
}

/** Format an ISO date as a short human label (e.g. "Aug 27"). */
export function shortDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
