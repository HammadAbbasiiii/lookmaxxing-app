// Typed API endpoint functions (§13.2). Each wraps `apiFetch` and decodes the
// response through a defensive Zod schema so a malformed payload never throws
// into the UI.

import { apiFetch, apiFetchUpload } from "@/lib/api/client";
import {
  decode,
  AnalysisSchema,
  type Analysis,
  CategoriesSchema,
  type CategoriesResponse,
  CheckinSchema,
  type CheckinResult,
  CompareSchema,
  type Compare,
  DashboardSchema,
  emptyDashboard,
  type Dashboard,
  DeleteAccountSchema,
  type DeleteAccountResult,
  ExploreSchema,
  type Explore,
  OnboardingSchema,
  type OnboardingResult,
  PhotoStatusSchema,
  type PhotoStatus,
  PlanSchema,
  emptyPlan,
  type Plan,
  type Product,
  ProductsSchema,
  type ProductsResponse,
  ProgressSchema,
  type Progress,
  SaveUploadSchema,
  type SaveUpload,
  TokenSchema,
  type TokenResponse,
  UploadSignatureSchema,
  type UploadSignature,
  UserSchema,
  emptyUser,
  type User,
  EntitlementsSchema,
  emptyEntitlements,
  type Entitlements,
  CoachSchema,
  type Coach,
  ReportSchema,
  type Report,
  InsightsSchema,
  emptyInsights,
  type Insights,
  HarmonySchema,
  emptyHarmony,
  type Harmony,
  LatestPhotoSchema,
  type LatestPhoto,
  CheckoutSchema,
  type Checkout,
  GlowStateResponseSchema,
  type GlowStateResponse,
  GlowOpenResponseSchema,
  type GlowOpenResponse,
  GlowRevealsResponseSchema,
  type GlowReveal,
  ArcStateSchema,
  type ArcState,
  ArcClaimSchema,
  type ArcClaim,
  ArcBadgeSchema,
  type ArcBadge,
  GlowupFeedSchema,
  type GlowupFeed,
  GlowupConsentSchema,
  type GlowupConsent,
  GlowupMovieSchema,
  type GlowupMovie,
} from "@/lib/zod";

// ── Auth ────────────────────────────────────────────────────────────
export async function signup(
  email: string,
  password: string,
  fullName?: string,
): Promise<User> {
  const data = await apiFetch<unknown>("/auth/signup", {
    method: "POST",
    body: { email, password, full_name: fullName?.trim() || null },
  });
  return decode(UserSchema, data, emptyUser());
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  // Backend uses OAuth2PasswordRequestForm → form-urlencoded `username`+`password`.
  const data = await apiFetch<unknown>("/auth/login", {
    method: "POST",
    form: true,
    body: { username: email.trim().toLowerCase(), password },
  });
  return decode(TokenSchema, data, { access_token: "", token_type: "bearer", user_id: "", email: "" });
}

export async function getMe(): Promise<User> {
  const data = await apiFetch<unknown>("/auth/me");
  return decode(UserSchema, data, emptyUser());
}

export async function logout(): Promise<void> {
  await apiFetch<unknown>("/auth/logout", { method: "POST" });
}

export async function requestPasswordReset(email: string): Promise<{ message: string }> {
  const data = await apiFetch<unknown>("/auth/forgot-password", {
    method: "POST",
    body: { email: email.trim().toLowerCase() },
  });
  const root = data && typeof data === "object" ? (data as Record<string, unknown>) : {};
  return { message: typeof root.message === "string" ? root.message : "" };
}

export async function resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
  const data = await apiFetch<unknown>("/auth/reset-password", {
    method: "POST",
    body: { token, new_password: newPassword },
  });
  const root = data && typeof data === "object" ? (data as Record<string, unknown>) : {};
  return { message: typeof root.message === "string" ? root.message : "" };
}

export async function verifyResetToken(token: string): Promise<boolean> {
  const qs = new URLSearchParams({ token }).toString();
  await apiFetch<unknown>(`/auth/reset-password/verify?${qs}`);
  return true;
}

// ── Upload / analysis (critical path §4.4) ──────────────────────────
export async function getUploadSignature(): Promise<UploadSignature> {
  const data = await apiFetch<unknown>("/upload/signature");
  return decode(UploadSignatureSchema, data, {
    signature: "",
    timestamp: 0,
    cloud_name: "",
    api_key: "",
    folder: "",
    public_id: "",
    upload_preset: undefined,
  });
}

// NOTE: /upload/save takes `file_url` and `public_id` as QUERY params (FastAPI
// simple-type params), not a JSON/form body.
export async function saveDirectUpload(fileUrl: string, publicId: string): Promise<SaveUpload> {
  const qs = new URLSearchParams({ file_url: fileUrl, public_id: publicId }).toString();
  const data = await apiFetch<unknown>(`/upload/save?${qs}`, { method: "POST" });
  return decode(SaveUploadSchema, data, { photo_id: "", file_url: fileUrl, is_baseline: false, week_number: 1 });
}

export async function analyzePhoto(photoId: string): Promise<void> {
  await apiFetchUpload<unknown>(`/photos/analyze/${photoId}`, { method: "POST" });
}

export async function getPhotoStatus(photoId: string): Promise<PhotoStatus> {
  const data = await apiFetch<unknown>(`/photos/${photoId}/status`);
  return decode(PhotoStatusSchema, data, {
    id: photoId,
    analysis_status: "pending",
    score: null,
    potential_score: null,
    raw_score: null,
    model_used: null,
    improvement_potential: null,
    category_breakdown: null,
    strengths: null,
    weaknesses: null,
    error: null,
    message: null,
  });
}

export async function getAnalysis(photoId: string): Promise<Analysis> {
  const data = await apiFetch<unknown>(`/analysis/${photoId}`);
  return decode(AnalysisSchema, data, {
    photo_id: photoId,
    file_url: "",
    scores: { overall: null, symmetry: null, skin: null, jawline: null, eyes: null },
    face_shape: null,
    is_baseline: false,
    analyzed_at: null,
  });
}

// ── Dashboard ───────────────────────────────────────────────────────
export async function getDashboard(): Promise<Dashboard> {
  const data = await apiFetch<unknown>("/dashboard");
  return decode(DashboardSchema, data, emptyDashboard());
}

// ── Plan ────────────────────────────────────────────────────────────
export async function getPlan(): Promise<Plan> {
  const data = await apiFetch<unknown>("/plan");
  return decode(PlanSchema, data, emptyPlan());
}

export async function postPlanCheckin(
  completedTasks: string[],
  notes?: string,
): Promise<CheckinResult> {
  const data = await apiFetch<unknown>("/plan/checkin", {
    method: "POST",
    body: { completed_tasks: completedTasks, notes: notes ?? "" },
  });
  return decode(CheckinSchema, data, {
    success: false,
    current_day: 0,
    current_week: 0,
    current_phase: "",
    days_remaining: 0,
    total_tasks_today: 0,
    tasks_completed: 0,
    tasks_remaining: 0,
    is_plan_complete: false,
    streak: 0,
    streak_message: "",
    longest_streak: 0,
    total_checkins: 0,
    milestone: null,
  });
}
// ── Progress ────────────────────────────────────────────────────────
export async function getProgress(): Promise<Progress> {
  const data = await apiFetch<unknown>("/analysis/progress/all");
  return decode(ProgressSchema, data, {
    photos: [],
    progress: null,
  });
}

export async function getCompare(): Promise<Compare> {
  const data = await apiFetch<unknown>("/progress/photos/compare");
  return decode(CompareSchema, data, {
    baseline: { id: "", file_url: "", score: null, captured_at: null },
    latest: null,
    score_change: null,
    trend: "stable",
    weeks_progressed: 0,
  });
}

export interface Milestones {
  completed: { day: number; title: string; emoji: string }[];
  upcoming: { day: number; title: string; days_remaining: number; emoji: string }[];
  next: { day: number; title: string; days_remaining: number; emoji: string } | null;
}

export async function getMilestones(): Promise<Milestones> {
  const data = await apiFetch<unknown>("/progress/milestones");
  const fallback: Milestones = { completed: [], upcoming: [], next: null };
  if (!data || typeof data !== "object") return fallback;
  const raw = data as Record<string, unknown>;
  const pick = (item: unknown, key: string): string =>
    item && typeof item === "object" && key in (item as object)
      ? String((item as Record<string, unknown>)[key] ?? "")
      : "";
  const num = (item: unknown, key: string): number => {
    const v = item && typeof item === "object" ? (item as Record<string, unknown>)[key] : undefined;
    return typeof v === "number" ? v : 0;
  };
  const completed = (Array.isArray(raw.completed) ? raw.completed : []).map((m) => ({
    day: num(m, "day"),
    title: pick(m, "title") || pick(m, "message") || "Milestone",
    emoji: pick(m, "emoji") || "🏆",
  }));
  const upcoming = (Array.isArray(raw.upcoming) ? raw.upcoming : []).map((m) => ({
    day: num(m, "day"),
    title: pick(m, "title") || pick(m, "message") || "Milestone",
    days_remaining: num(m, "days_remaining") || num(m, "days_until") || 0,
    emoji: pick(m, "emoji") || "🔥",
  }));
  const nextRaw = raw.next_milestone ?? raw.next ?? null;
  return {
    completed,
    upcoming,
    next:
      nextRaw && typeof nextRaw === "object"
        ? {
            day: num(nextRaw, "day"),
            title: pick(nextRaw, "title") || pick(nextRaw, "message") || "Milestone",
            days_remaining: num(nextRaw, "days_remaining") || num(nextRaw, "days_until") || 0,
            emoji: pick(nextRaw, "emoji") || "🎯",
          }
        : null,
  };
}

// ── Explore ─────────────────────────────────────────────────────────
export async function getExplore(): Promise<Explore> {
  const data = await apiFetch<unknown>("/explore");
  return decode(ExploreSchema, data, { success: false, transformations: [], articles: [], total: 0 });
}

// ── Products ────────────────────────────────────────────────────────
export async function getProductRecommendations(
  tier: string,
  maxResults = 8,
): Promise<ProductsResponse> {
  const data = await apiFetch<unknown>(
    `/products/recommendations?tier=${encodeURIComponent(tier)}&max_results=${maxResults}`,
  );
  // Backend returns each recommendation as { product: {...}, reason, category, tier }.
  // Flatten to the flat Product shape the UI cards expect (defensive on both shapes).
  const root =
    data && typeof data === "object" ? (data as Record<string, unknown>) : {};
  const items = Array.isArray(root.recommendations) ? root.recommendations : [];
  const s = (v: unknown): string => (typeof v === "string" ? v : "");
  const n = (v: unknown): number | null =>
    typeof v === "number" && Number.isFinite(v) ? v : null;
  const n0 = (v: unknown): number =>
    typeof v === "number" && Number.isFinite(v) ? v : 0;
  const recommendations = items.map((item) => {
    const w =
      item && typeof item === "object" ? (item as Record<string, unknown>) : {};
    const p =
      w.product && typeof w.product === "object"
        ? (w.product as Record<string, unknown>)
        : {};
    return {
      id: s(p.id ?? w.id),
      name: s(p.name ?? w.name),
      category: s(w.category ?? p.category),
      price: n(p.price ?? w.price),
      currency: s(p.currency ?? w.currency) || "USD",
      rating: n(p.rating ?? w.rating),
      review_count: n0(p.reviews_count ?? p.review_count ?? w.review_count),
      url: s(p.affiliate_link ?? p.url ?? w.url),
      image_url: p.image_url ?? w.image_url ?? null,
      description: s(w.reason ?? p.social_proof ?? p.description),
      tier: s(w.tier ?? p.tier) || "mid_range",
      commission: null,
    };
  });
  const next: Record<string, unknown> = { ...root, recommendations };
  return decode(ProductsSchema, next, { success: false, recommendations: [], total: 0, message: "" });
}

export async function getCategories(): Promise<CategoriesResponse> {
  const data = await apiFetch<unknown>("/products/categories");
  // Backend returns { id, name, product_count } — map to the Category shape.
  const root = data && typeof data === "object" ? (data as Record<string, unknown>) : {};
  const raw = Array.isArray(root.categories) ? root.categories : [];
  const categories = raw.map((c) => {
    const w = c && typeof c === "object" ? (c as Record<string, unknown>) : {};
    const name = typeof w.name === "string" ? w.name : "";
    return {
      id: typeof w.id === "string" ? w.id : "",
      name,
      label: name,
      count: typeof w.product_count === "number" ? w.product_count : 0,
      emoji: "",
    };
  });
  return decode(
    CategoriesSchema,
    { success: true, categories, total: categories.length },
    { success: false, categories: [], total: 0 },
  );
}

export async function getProductsByCategory(
  category: string,
  tier?: string | null,
): Promise<Product[]> {
  const qs = tier ? `?tier=${encodeURIComponent(tier)}` : "";
  const data = await apiFetch<unknown>(`/products/category/${encodeURIComponent(category)}${qs}`);
  const root = data && typeof data === "object" ? (data as Record<string, unknown>) : {};
  const items = Array.isArray(root.products) ? root.products : [];
  const s = (v: unknown): string => (typeof v === "string" ? v : "");
  const n = (v: unknown): number | null =>
    typeof v === "number" && Number.isFinite(v) ? v : null;
  const n0 = (v: unknown): number =>
    typeof v === "number" && Number.isFinite(v) ? v : 0;
  return items.map((item) => {
    const w = item && typeof item === "object" ? (item as Record<string, unknown>) : {};
    const img = w.image_url;
    return {
      id: s(w.id),
      name: s(w.name),
      category: s(w.category),
      price: n(w.price),
      currency: s(w.currency) || "USD",
      rating: n(w.rating),
      review_count: n0(w.reviews_count ?? w.review_count),
      url: s(w.affiliate_link ?? w.url),
      image_url: typeof img === "string" ? img : null,
      description: s(w.social_proof ?? w.description),
      tier: s(w.tier) || "mid_range",
      commission: null,
    };
  });
}

// ── Profile ─────────────────────────────────────────────────────────
export interface ProfileUpdate {
  full_name?: string;
  age?: number;
  gender?: string;
  goals?: string[];
  height?: number;
  weight?: number;
  location?: string;
  bio?: string;
  skin_type?: string;
  skin_concerns?: string[];
  commitment?: string;
}

export async function getProfile(): Promise<User> {
  const data = await apiFetch<unknown>("/profile");
  return decode(UserSchema, data, emptyUser());
}

export async function putProfile(update: ProfileUpdate): Promise<User> {
  const data = await apiFetch<unknown>("/profile", { method: "PUT", body: update });
  return decode(UserSchema, data, emptyUser());
}

export async function completeOnboarding(): Promise<OnboardingResult> {
  const data = await apiFetch<unknown>("/profile/onboarding", { method: "POST" });
  return decode(OnboardingSchema, data, { success: false, message: "", onboarding_completed: false });
}

export async function deleteAccount(): Promise<DeleteAccountResult> {
  const data = await apiFetch<unknown>("/profile/delete", { method: "DELETE" });
  return decode(DeleteAccountSchema, data, { success: false, message: "" });
}

// ── Entitlements / premium ─────────────────────────────────────────
export async function getEntitlements(): Promise<Entitlements> {
  const data = await apiFetch<unknown>("/entitlements");
  return decode(EntitlementsSchema, data, emptyEntitlements());
}

export async function getCoach(): Promise<Coach> {
  const data = await apiFetch<unknown>("/coach");
  return decode(CoachSchema, data, {
    date: "",
    tier: "pro",
    message: "",
    focus: null,
    tasks: [],
    score_context: "",
    source: "template",
  });
}

export async function getReport(photoId: string): Promise<Report> {
  const data = await apiFetch<unknown>(`/analysis/${photoId}/report`);
  return decode(ReportSchema, data, {
    photo_id: photoId,
    overall_score: null,
    potential_score: null,
    improvement_gap: null,
    face_shape: null,
    categories: [],
    weakest_areas: [],
    strongest_areas: [],
    strengths: [],
    weaknesses: [],
    improvement_potential: "",
    recommendations: { skincare: [], grooming: "", exercise: [], diet: [] },
  });
}

export async function getAnalysisInsights(photoId: string): Promise<Insights> {
  const data = await apiFetch<unknown>(`/analysis/${photoId}/insights`);
  return decode(InsightsSchema, data, emptyInsights(photoId));
}

export async function getAnalysisHarmony(photoId: string): Promise<Harmony> {
  const data = await apiFetch<unknown>(`/analysis/${photoId}/harmony`);
  return decode(HarmonySchema, data, emptyHarmony(photoId));
}

export async function getLatestPhoto(): Promise<LatestPhoto> {
  const data = await apiFetch<unknown>("/progress/photos/latest");
  return decode(LatestPhotoSchema, data, {
    id: "",
    file_url: "",
    score: null,
    is_baseline: false,
    week_number: 1,
    captured_at: null,
  });
}

export async function createCheckout(tier: "pro" | "elite", annual: boolean): Promise<Checkout> {
  const data = await apiFetch<unknown>("/payments/checkout", {
    method: "POST",
    body: { tier, annual },
  });
  return decode(CheckoutSchema, data, { checkout_url: null });
}

export async function testUpgrade(tier: "pro" | "elite"): Promise<{ success: boolean; tier: string }> {
  const data = await apiFetch<unknown>("/payments/test-upgrade", { method: "POST", body: { tier } });
  const root = data && typeof data === "object" ? (data as Record<string, unknown>) : {};
  return { success: Boolean(root.success), tier: typeof root.tier === "string" ? root.tier : tier };
}

// ── Momentum: Glow (daily reveal) ──────────────────────────────────
const emptyGlowReveal = (): GlowReveal => ({
  id: "",
  day: 1,
  rarity: "common",
  reward_type: "micro_win",
  payload: {
    kind: "", emoji: "", headline: "", body: "", photo_url: null, blur_px: null,
    before_url: null, after_url: null, before_score: null, after_score: null,
    delta: null, share_text: null,
  },
  opened_at: null,
});

const emptyGlowState = () => ({
  journey_day: 1,
  glow_streak: 0,
  longest_glow_streak: 0,
  opens_count: 0,
  blur_next: 24,
  full_reveal: { eligible: false, unlocked: false },
  weights: { common: 70, rare: 24, epic: 5, legendary: 1 },
});

export async function getGlowState(): Promise<GlowStateResponse> {
  const data = await apiFetch<unknown>("/glow/state");
  return decode(GlowStateResponseSchema, data, {
    can_open: false,
    opened_today: false,
    today_reveal: null,
    state: emptyGlowState(),
  });
}

export async function openGlow(): Promise<GlowOpenResponse> {
  const data = await apiFetch<unknown>("/glow/open", { method: "POST" });
  return decode(GlowOpenResponseSchema, data, {
    already_opened: false,
    reveal: emptyGlowReveal(),
    state: emptyGlowState(),
  });
}

export async function getGlowReveals(): Promise<{ reveals: GlowReveal[]; total: number }> {
  const data = await apiFetch<unknown>("/glow/reveals");
  return decode(GlowRevealsResponseSchema, data, { reveals: [], total: 0 });
}

// ── Momentum: The Arc (XP / levels / quests / badges) ───────────────
const emptyArcState = (): ArcState => ({
  level: 1,
  total_xp: 0,
  xp_to_next: 100,
  title: "",
  archetype: "Rookie",
  milestone_title: null,
  premium: false,
  today_quests: [],
  badges: [],
  skill_tree: [],
});

export async function getArcState(): Promise<ArcState> {
  const data = await apiFetch<unknown>("/arc/state");
  return decode(ArcStateSchema, data, emptyArcState());
}

export async function claimArcQuest(questId: string): Promise<ArcClaim> {
  const data = await apiFetch<unknown>(`/arc/quests/${questId}/claim`, { method: "POST" });
  return decode(ArcClaimSchema, data, {
    xp_awarded: 0, level: 1, total_xp: 0, leveled_up: false, new_title: null,
  });
}

export async function getArcBadges(): Promise<{ badges: ArcBadge[] }> {
  const data = await apiFetch<unknown>("/arc/badges");
  const root = data && typeof data === "object" ? (data as Record<string, unknown>) : {};
  const raw = Array.isArray(root.badges) ? root.badges : [];
  const badges = raw.map((b) =>
    decode(ArcBadgeSchema, b, { badge_key: "", name: "", emoji: "🏅", description: "", unlocked_at: null }),
  );
  return { badges };
}

// ── Momentum: Glow-Ups (feed + movie) ───────────────────────────────
export async function getGlowupsFeed(cursor = 0): Promise<GlowupFeed> {
  const data = await apiFetch<unknown>(`/glowups/feed?cursor=${cursor}`);
  return decode(GlowupFeedSchema, data, { items: [], next_cursor: null, locked: false });
}

export async function setGlowupsConsent(shareEnabled: boolean): Promise<GlowupConsent> {
  const data = await apiFetch<unknown>("/glowups/consent", {
    method: "POST",
    body: { share_enabled: shareEnabled },
  });
  return decode(GlowupConsentSchema, data, { share_enabled: false, error: null });
}

export async function getGlowupsConsent(): Promise<GlowupConsent> {
  const data = await apiFetch<unknown>("/glowups/consent");
  return decode(GlowupConsentSchema, data, { share_enabled: false, error: null });
}

export async function getGlowupsMovie(): Promise<GlowupMovie> {
  const data = await apiFetch<unknown>("/glowups/movie");
  return decode(GlowupMovieSchema, data, {
    status: "pending", trailers: [], full_movie_url: null, photo_urls: [], delta: 0,
  });
}

export async function generateGlowupsMovie(): Promise<{ job_id: string | null; status: string; throttled?: boolean }> {
  const data = await apiFetch<unknown>("/glowups/movie/generate", { method: "POST" });
  const root = data && typeof data === "object" ? (data as Record<string, unknown>) : {};
  return {
    job_id: typeof root.job_id === "string" ? root.job_id : null,
    status: typeof root.status === "string" ? root.status : "pending",
    throttled: Boolean(root.throttled),
  };
}

export async function reportGlowupsItem(itemId: string): Promise<{ reported: boolean }> {
  const data = await apiFetch<unknown>(`/glowups/items/${itemId}/report`, { method: "POST" });
  const root = data && typeof data === "object" ? (data as Record<string, unknown>) : {};
  return { reported: Boolean(root.reported) };
}

