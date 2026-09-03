// Central app constants — single source of truth for copy, tiers, goals, etc.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "https://lookmaxx-api.onrender.com/api/v1";

export const CLOUDINARY_UPLOAD_URL = "https://api.cloudinary.com/v1_1";

// TanStack Query stale times (§7.4). Gating reads (/auth/me) are never stale-cached.
export const STALE = {
  me: 0,
  dashboard: 30_000,
  plan: 30_000,
  analysis: 60_000,
  explore: 5 * 60_000,
  products: 5 * 60_000,
} as const;

// Analysis polling cadence + cap (§4.4, §8.6).
export const POLL_INTERVAL_MS = 1_500;
export const POLL_MAX_MS = 60_000;

// Upload limits (§5.10).
export const MAX_FILE_SIZE_MB = 10;
export const MAX_DIMENSION_PX = 1200;
export const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/heic"] as const;

// Score display guardrails (§6.1, §20 — deterministic scores clamp 30–95).
export const SCORE_MIN = 30;
export const SCORE_MAX = 95;

// Onboarding choices (§8.4).
export const GENDER_OPTIONS = [
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
  { value: "other", label: "Other" },
] as const;

export const GOAL_OPTIONS = [
  { value: "improve_skin", label: "Skin", emoji: "✨" },
  { value: "jawline", label: "Jawline", emoji: "🗿" },
  { value: "confidence", label: "Confidence", emoji: "💪" },
  { value: "symmetry", label: "Symmetry", emoji: "⚖️" },
  { value: "general", label: "General", emoji: "🎯" },
] as const;

export const COMMITMENT_OPTIONS = [
  { value: "casual", label: "Casual" },
  { value: "consistent", label: "Consistent" },
  { value: "locked_in", label: "Locked in" },
] as const;

export const SKIN_TYPE_OPTIONS = [
  { value: "oily", label: "Oily" },
  { value: "dry", label: "Dry" },
  { value: "combination", label: "Combination" },
  { value: "normal", label: "Normal" },
  { value: "sensitive", label: "Sensitive" },
] as const;

export const SKIN_CONCERN_OPTIONS = [
  { value: "acne", label: "Acne / breakouts", emoji: "🔴" },
  { value: "dark_spots", label: "Dark spots", emoji: "🟤" },
  { value: "redness", label: "Redness", emoji: "🌡️" },
  { value: "dullness", label: "Dullness", emoji: "😶‍🌫️" },
  { value: "fine_lines", label: "Fine lines", emoji: "〰️" },
  { value: "oiliness", label: "Excess oil", emoji: "💧" },
] as const;

// Products budget tiers (§8.12).
export const PRODUCT_TIERS = [
  { value: "budget", label: "Budget" },
  { value: "mid_range", label: "Mid" },
  { value: "premium", label: "Premium" },
] as const;

// Paywall tiers (§12.1). Prices are the marketing anchor; the backend is the
// authoritative gate. Until /payments/* ships, /upgrade shows a waitlist.
export const PLANS = {
  free: {
    tier: "free",
    name: "Free",
    monthly: 0,
    blurb: "1 analysis, streak tracking, baseline score.",
  },
  pro: {
    tier: "pro",
    name: "Pro",
    monthly: 9.99,
    blurb: "Unlimited analyses, 90-day plan, Glow-Up Forecast, percentile rank & your look-alike archetype.",
    highlight: true,
  },
  elite: {
    tier: "elite",
    name: "Elite",
    monthly: 19.99,
    blurb: "Everything in Pro + golden-ratio harmony map, weekly blueprint & a shareable glow-up card.",
  },
} as const;

export const ANNUAL_DISCOUNT_PCT = 58;

// Score labels (mirrors backend score_labels) — neutral-encouraging, never shaming.
export function scoreLabel(score: number): string {
  if (score >= 80) return "Elite symmetry";
  if (score >= 60) return "Strong features";
  if (score >= 40) return "Solid foundation";
  return "Room to grow";
}
