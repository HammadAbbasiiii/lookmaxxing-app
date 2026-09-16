// Tier vocabulary — one place that decides what "Pro" and "Elite" mean in the UI.
//
// The server is the real gate (`require_pro` / `require_elite` in
// backend/app/dependencies.py) and the feature matrix lives in
// `backend/app/services/entitlements_service.py`. Everything here is *presentation*:
// labels, chips and "is this unlocked for me" checks, so no two screens can
// describe the same plan differently.

export type Tier = "free" | "pro" | "elite";

/** Minimum paid tier a surface can require. */
export type PaidTier = Exclude<Tier, "free">;

export const TIER_RANK: Record<Tier, number> = { free: 0, pro: 1, elite: 2 };

/** Any tier string from the API → a known Tier (unknown values read as free). */
export function normalizeTier(value?: string | null): Tier {
  const v = (value ?? "").toLowerCase();
  return v === "pro" || v === "elite" ? v : "free";
}

/** Display name — always use this instead of hand-written "Pro"/"Elite" strings. */
export function tierLabel(tier: Tier): "Free" | "Pro" | "Elite" {
  return tier === "free" ? "Free" : tier === "pro" ? "Pro" : "Elite";
}

/** True when `tier` is at least `required` (Pro unlocks Pro; Elite unlocks both). */
export function hasTier(
  tier: Tier | string | null | undefined,
  required: Tier,
): boolean {
  return TIER_RANK[normalizeTier(tier)] >= TIER_RANK[required];
}

/** Pro *or* Elite — the check almost every "is premium unlocked?" call wants. */
export function isPaidTier(tier?: string | null): boolean {
  return hasTier(tier, "pro");
}

/** Elite only — the golden-ratio / movie / Day-90 surfaces. */
export function isEliteTier(tier?: string | null): boolean {
  return hasTier(tier, "elite");
}
