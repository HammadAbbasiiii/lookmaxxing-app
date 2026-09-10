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

// ── Paywall tiers (§12.1) ────────────────────────────────────────────
// Prices are the marketing anchor; the backend is the authoritative gate.
// Display order is intentional (psychology, see PSYCHOLOGY.md §5): Elite first
// (price anchor) → Pro (feels like a bargain) → Free (low barrier).

export const PLAN_ORDER = ["elite", "pro", "free"] as const;

// Annual prices are fixed in Stripe (Pro £50.40, Elite £100.80). We list them
// explicitly so the UI never drifts from what the customer is actually charged.
export const ANNUAL_DISCOUNT_PCT = 58;

// "£1 first month" offer — Pro monthly only, one-time. The backend flags
// User.has_used_first_month_offer to prevent repeat use.
export const FIRST_MONTH_PRICE = 1;

// 7-day free trial on Elite (Stripe collects the card up front).
export const ELITE_TRIAL_DAYS = 7;

export const PLANS = {
  free: {
    tier: "free",
    name: "Free",
    badge: "Start Here",
    monthly: 0,
    annual: 0,
    annualOriginal: 0,
    perMonth: 0,
    blurb: "1 analysis, baseline score, streak tracking.",
    features: ["1 analysis", "Basic score", "Streak tracking"],
  },
  pro: {
    tier: "pro",
    name: "Pro",
    badge: "Most Popular",
    monthly: 9.99,
    annual: 50.4,
    annualOriginal: 119.88,
    perMonth: 4.2,
    blurb: "Unlimited analyses, full 90-day plan, product recs & progress tracking.",
    features: [
      "Unlimited analyses",
      "Full 90-day plan + check-ins",
      "Product recommendations",
      "Progress tracking",
      "Glow-Up Forecast (Day 30/60/90)",
      "Daily AI coach",
    ],
  },
  elite: {
    tier: "elite",
    name: "Elite",
    badge: "Best Value",
    monthly: 19.99,
    annual: 100.8,
    annualOriginal: 239.88,
    perMonth: 8.4,
    blurb: "Everything in Pro + personal coaching, priority support & exclusive content.",
    features: [
      "Everything in Pro",
      "Personal coaching (1:1 Q&A)",
      "Priority support",
      "Exclusive content",
      "Golden-Ratio Harmony Map",
      "Shareable Glow-Up Card",
    ],
  },
} as const;

// Score labels (mirrors backend score_labels) — neutral-encouraging, never shaming.
export function scoreLabel(score: number): string {
  if (score >= 80) return "Elite symmetry";
  if (score >= 60) return "Strong features";
  if (score >= 40) return "Solid foundation";
  return "Room to grow";
}
