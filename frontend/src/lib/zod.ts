// Defensive Zod schemas mirroring backend Pydantic models (§7.3 #4, §13.2).
//
// Every field decodes with a `.catch()` fallback so a malformed, missing, or
// wrong-typed field degrades to a safe default instead of throwing. TypeScript
// types are generated from these schemas so API drift is caught at compile time.

import { z } from "zod";

/** Safe decode: on any failure return the provided fallback (never throws). */
export function decode<S extends z.ZodTypeAny>(
  schema: S,
  data: unknown,
  fallback: z.infer<S>,
): z.infer<S> {
  const result = schema.safeParse(data);
  return result.success ? result.data : fallback;
}

// ── Auth ────────────────────────────────────────────────────────────
export const UserSchema = z.object({
  id: z.string().catch(""),
  email: z.string().catch(""),
  full_name: z.string().nullable().catch(null),
  age: z.number().nullable().catch(null),
  gender: z.string().nullable().catch(null),
  goals: z.array(z.string()).nullable().catch(null),
  height: z.number().nullable().catch(null),
  weight: z.number().nullable().catch(null),
  location: z.string().nullable().catch(null),
  bio: z.string().nullable().catch(null),
  skin_type: z.string().nullable().catch(null),
  skin_concerns: z.array(z.string()).nullable().catch(null),
  commitment: z.string().nullable().catch(null),
  onboarding_completed: z.boolean().catch(false),
  subscription_tier: z.string().catch("free"),
  is_subscribed: z.boolean().catch(false),
  is_admin: z.boolean().catch(false),
  total_checkins: z.number().catch(0),
  current_streak: z.number().catch(0),
  longest_streak: z.number().catch(0),
  current_day: z.number().catch(0),
  created_at: z.string().catch(""),
});
export type User = z.infer<typeof UserSchema>;

export const emptyUser = (): User => ({
  id: "",
  email: "",
  full_name: null,
  age: null,
  gender: null,
  goals: null,
  height: null,
  weight: null,
  location: null,
  bio: null,
  skin_type: null,
  skin_concerns: null,
  commitment: null,
  onboarding_completed: false,
  subscription_tier: "free",
  is_subscribed: false,
  is_admin: false,
  total_checkins: 0,
  current_streak: 0,
  longest_streak: 0,
  current_day: 0,
  created_at: "",
});

export const TokenSchema = z.object({
  access_token: z.string().catch(""),
  token_type: z.string().catch("bearer"),
  user_id: z.string().catch(""),
  email: z.string().catch(""),
});
export type TokenResponse = z.infer<typeof TokenSchema>;
// ── Photos / analysis ───────────────────────────────────────────────
export const PhotoStatusSchema = z.object({
  id: z.string().catch(""),
  analysis_status: z.string().catch("pending"),
  score: z.number().nullable().catch(null),
  potential_score: z.number().nullable().catch(null),
  raw_score: z.number().nullable().catch(null),
  model_used: z.boolean().nullable().catch(null),
  improvement_potential: z.string().nullable().catch(null),
  category_breakdown: z.record(z.string(), z.number()).nullable().catch(null),
  strengths: z.array(z.string()).nullable().catch(null),
  weaknesses: z.array(z.string()).nullable().catch(null),
  error: z.string().nullable().catch(null),
  message: z.string().nullable().catch(null),
});
export type PhotoStatus = z.infer<typeof PhotoStatusSchema>;

export const AnalysisSchema = z.object({
  photo_id: z.string().catch(""),
  file_url: z.string().catch(""),
  scores: z
    .object({
      overall: z.number().nullable().catch(null),
      symmetry: z.number().nullable().catch(null),
      skin: z.number().nullable().catch(null),
      jawline: z.number().nullable().catch(null),
      eyes: z.number().nullable().catch(null),
    })
    .catch({ overall: null, symmetry: null, skin: null, jawline: null, eyes: null }),
  face_shape: z.string().nullable().catch(null),
  is_baseline: z.boolean().catch(false),
  analyzed_at: z.string().nullable().catch(null),
});
export type Analysis = z.infer<typeof AnalysisSchema>;

export const UploadSignatureSchema = z.object({
  signature: z.string().catch(""),
  timestamp: z.number().catch(0),
  cloud_name: z.string().catch(""),
  api_key: z.string().catch(""),
  folder: z.string().catch(""),
  public_id: z.string().catch(""),
  upload_preset: z.string().optional().catch(undefined),
});
export type UploadSignature = z.infer<typeof UploadSignatureSchema>;

export const SaveUploadSchema = z.object({
  photo_id: z.string().catch(""),
  file_url: z.string().catch(""),
  is_baseline: z.boolean().catch(false),
  week_number: z.number().catch(1),
});
export type SaveUpload = z.infer<typeof SaveUploadSchema>;
// ── Dashboard ───────────────────────────────────────────────────────
export const DashboardSchema = z.object({
  profile: UserSchema.catch(emptyUser()),
  plan: z
    .object({
      has_plan: z.boolean().catch(false),
      current_day: z.number().catch(0),
      total_days: z.number().catch(90),
      progress_percentage: z.number().catch(0),
      days_remaining: z.number().catch(90),
      phase: z.string().catch(""),
      current_phase: z.string().catch(""),
    })
    .nullable()
    .catch(null),
  progress: z
    .object({
      initial_score: z.number().nullable().catch(null),
      current_score: z.number().nullable().catch(null),
      improvement: z.number().nullable().catch(null),
      current_streak: z.number().catch(0),
      longest_streak: z.number().catch(0),
      total_checkins: z.number().catch(0),
      checked_in_today: z.boolean().catch(false),
    })
    .nullable()
    .catch(null),
  milestones: z
    .object({
      next: z
        .object({
          day: z.number().catch(0),
          label: z.string().catch(""),
          days_until: z.number().catch(0),
        })
        .nullable()
        .catch(null),
      completed: z.array(z.unknown()).catch([]),
    })
    .catch({ next: null, completed: [] }),
  next_action: z
    .object({
      task: z.string().catch(""),
      time: z.string().catch(""),
      description: z.string().catch(""),
    })
    .nullable()
    .catch(null),
});
export type Dashboard = z.infer<typeof DashboardSchema>;

export const emptyDashboard = (): Dashboard => ({
  profile: emptyUser(),
  plan: null,
  progress: null,
  milestones: { next: null, completed: [] },
  next_action: null,
});
// ── Plan ────────────────────────────────────────────────────────────
const TaskSchema = z.preprocess(
  (raw) => {
    // Backend task shape is { task, time, duration_minutes, days }; the UI reads
    // { name, time, details }. Normalise so the task list never renders blank.
    if (raw && typeof raw === "object" && !Array.isArray(raw)) {
      const o = raw as Record<string, unknown>;
      if (typeof o.task === "string" && !o.name) {
        const parts: string[] = [];
        if (typeof o.duration_minutes === "number" && o.duration_minutes > 0) {
          parts.push(`${o.duration_minutes} min`);
        }
        if (Array.isArray(o.days) && o.days.length > 0) {
          parts.push((o.days as string[]).join(", "));
        }
        return { name: o.task, time: o.time ?? "", details: parts.join(" · ") };
      }
    }
    return raw;
  },
  z.object({
    name: z.string().catch(""),
    time: z.string().catch(""),
    details: z.string().catch(""),
  }),
);

const WeekTasksSchema = z.object({
  week: z.number().catch(0),
  daily_tasks: z.array(TaskSchema).catch([]),
});

export const PlanSchema = z.object({
  has_plan: z.boolean().catch(false),
  message: z.string().catch(""),
  plan_id: z.string().catch(""),
  photo_id: z.string().catch(""),
  baseline_score: z.number().nullable().catch(null),
  total_days: z.number().catch(90),
  current: z
    .object({
      day: z.number().catch(0),
      week: z.number().catch(1),
      phase: z.string().catch(""),
      phase_title: z.string().catch(""),
      phase_emotional_goal: z.string().catch(""),
      focus_areas: z.array(z.string()).catch([]),
    })
    .catch({ day: 0, week: 1, phase: "", phase_title: "", phase_emotional_goal: "", focus_areas: [] }),
  this_week: WeekTasksSchema.nullable().catch(null),
  todays_quote: z
    .object({
      day: z.number().catch(0),
      text: z.string().catch(""),
      author: z.string().catch(""),
    })
    .nullable()
    .catch(null),
  upcoming_milestone: z
    .object({
      day: z.number().catch(0),
      days_remaining: z.number().catch(0),
      details: z.unknown().catch(null),
    })
    .nullable()
    .catch(null),
  streak: z.number().catch(0),
  checked_in_today: z.boolean().catch(false),
  products: z.array(z.unknown()).catch([]),
  bonus_tip: z.string().catch(""),
  phases: z
    .object({
      phase_1: z.object({ days: z.string().catch(""), title: z.string().catch(""), complete: z.boolean().catch(false) }).catch({ days: "", title: "", complete: false }),
      phase_2: z.object({ days: z.string().catch(""), title: z.string().catch(""), complete: z.boolean().catch(false) }).catch({ days: "", title: "", complete: false }),
      phase_3: z.object({ days: z.string().catch(""), title: z.string().catch(""), complete: z.boolean().catch(false) }).catch({ days: "", title: "", complete: false }),
    })
    .catch({
      phase_1: { days: "", title: "", complete: false },
      phase_2: { days: "", title: "", complete: false },
      phase_3: { days: "", title: "", complete: false },
    }),
});
export type Plan = z.infer<typeof PlanSchema>;

export const emptyPlan = (): Plan => ({
  has_plan: false,
  message: "",
  plan_id: "",
  photo_id: "",
  baseline_score: null,
  total_days: 90,
  current: { day: 0, week: 1, phase: "", phase_title: "", phase_emotional_goal: "", focus_areas: [] },
  this_week: null,
  todays_quote: null,
  upcoming_milestone: null,
  streak: 0,
  checked_in_today: false,
  products: [],
  bonus_tip: "",
  phases: {
    phase_1: { days: "", title: "", complete: false },
    phase_2: { days: "", title: "", complete: false },
    phase_3: { days: "", title: "", complete: false },
  },
});

export const CheckinSchema = z.object({
  success: z.boolean().catch(false),
  current_day: z.number().catch(0),
  current_week: z.number().catch(0),
  current_phase: z.string().catch(""),
  days_remaining: z.number().catch(0),
  total_tasks_today: z.number().catch(0),
  tasks_completed: z.number().catch(0),
  tasks_remaining: z.number().catch(0),
  is_plan_complete: z.boolean().catch(false),
  streak: z.number().catch(0),
  streak_message: z.string().catch(""),
  longest_streak: z.number().catch(0),
  total_checkins: z.number().catch(0),
  milestone: z.unknown().nullable().catch(null),
});
export type CheckinResult = z.infer<typeof CheckinSchema>;
// ── Progress ────────────────────────────────────────────────────────
export const ProgressSchema = z.object({
  photos: z
    .array(
      z.object({
        photo_id: z.string().catch(""),
        score: z.number().nullable().catch(null),
        face_shape: z.string().nullable().catch(null),
        is_baseline: z.boolean().catch(false),
        date: z.string().nullable().catch(null),
        plan_phase: z.string().nullable().catch(null),
        plan_week: z.number().nullable().catch(null),
      }),
    )
    .catch([]),
  progress: z
    .object({
      baseline_score: z.number().nullable().catch(null),
      current_score: z.number().nullable().catch(null),
      score_change: z.number().nullable().catch(null),
      trend: z.string().catch("stable"),
      total_photos_analyzed: z.number().catch(0),
    })
    .nullable()
    .catch(null),
});
export type Progress = z.infer<typeof ProgressSchema>;

export const CompareSchema = z.object({
  baseline: z
    .object({
      id: z.string().catch(""),
      file_url: z.string().catch(""),
      score: z.number().nullable().catch(null),
      captured_at: z.string().nullable().catch(null),
    })
    .catch({ id: "", file_url: "", score: null, captured_at: null }),
  latest: z
    .object({
      id: z.string().catch(""),
      file_url: z.string().catch(""),
      score: z.number().nullable().catch(null),
      week_number: z.number().nullable().catch(null),
      captured_at: z.string().nullable().catch(null),
    })
    .nullable()
    .catch(null),
  score_change: z.number().nullable().catch(null),
  trend: z.string().catch("stable"),
  weeks_progressed: z.number().catch(0),
});
export type Compare = z.infer<typeof CompareSchema>;
// ── Explore ─────────────────────────────────────────────────────────
export const TransformationSchema = z.object({
  id: z.string().catch(""),
  username: z.string().catch(""),
  before_score: z.number().catch(0),
  after_score: z.number().catch(0),
  // Raw face URLs are present in the API response but MUST NOT be rendered
  // until the blur/opt-in privacy fix ships (§5.11, §20.5).
  before_image_url: z.string().catch(""),
  after_image_url: z.string().catch(""),
});
export type Transformation = z.infer<typeof TransformationSchema>;

export const ArticleSchema = z.object({
  id: z.string().catch(""),
  title: z.string().catch(""),
  summary: z.string().catch(""),
  url: z.string().catch(""),
  image_url: z.string().nullable().catch(null),
});
export type Article = z.infer<typeof ArticleSchema>;

export const ExploreSchema = z.object({
  success: z.boolean().catch(false),
  transformations: z.array(TransformationSchema).catch([]),
  articles: z.array(ArticleSchema).catch([]),
  total: z.number().catch(0),
});
export type Explore = z.infer<typeof ExploreSchema>;

// ── Products ────────────────────────────────────────────────────────
export const ProductSchema = z.object({
  id: z.string().catch(""),
  name: z.string().catch(""),
  category: z.string().catch(""),
  price: z.number().nullable().catch(null),
  currency: z.string().catch("USD"),
  rating: z.number().nullable().catch(null),
  review_count: z.number().catch(0),
  url: z.string().catch(""),
  image_url: z.string().nullable().catch(null),
  description: z.string().catch(""),
  tier: z.string().catch("mid_range"),
  commission: z.number().nullable().catch(null),
});
export type Product = z.infer<typeof ProductSchema>;

export const ProductsSchema = z.object({
  success: z.boolean().catch(false),
  recommendations: z.array(ProductSchema).catch([]),
  total: z.number().catch(0),
  message: z.string().catch(""),
});
export type ProductsResponse = z.infer<typeof ProductsSchema>;

export const CategorySchema = z.object({
  id: z.string().catch(""),
  name: z.string().catch(""),
  label: z.string().catch(""),
  count: z.number().catch(0),
  emoji: z.string().catch(""),
});
export const CategoriesSchema = z.object({
  success: z.boolean().catch(false),
  categories: z.array(CategorySchema).catch([]),
  total: z.number().catch(0),
});
export type CategoriesResponse = z.infer<typeof CategoriesSchema>;

// ── Profile mutations ──────────────────────────────────────────────
export const OnboardingSchema = z.object({
  success: z.boolean().catch(false),
  message: z.string().catch(""),
  onboarding_completed: z.boolean().catch(false),
});
export type OnboardingResult = z.infer<typeof OnboardingSchema>;

export const DeleteAccountSchema = z.object({
  success: z.boolean().catch(false),
  message: z.string().catch(""),
});
// ── Entitlements / premium ─────────────────────────────────────────
export const EntitlementFeatureSchema = z.object({
  key: z.string().catch(""),
  name: z.string().catch(""),
  description: z.string().catch(""),
  teaser: z.string().catch(""),
  tier: z.string().catch("pro"),
  locked: z.boolean().catch(true),
});
export type EntitlementFeature = z.infer<typeof EntitlementFeatureSchema>;

export const EntitlementsSchema = z.object({
  tier: z.string().catch("free"),
  is_subscribed: z.boolean().catch(false),
  subscription_end: z.string().nullable().catch(null),
  limits: z
    .object({
      analyses: z.object({
        used: z.number().catch(0),
        allowed: z.number().nullable().catch(null),
        unlimited: z.boolean().catch(false),
        remaining: z.number().nullable().catch(null),
      }),
      photos: z.number().catch(0),
    })
    .catch({ analyses: { used: 0, allowed: null, unlimited: false, remaining: null }, photos: 0 }),
  features: z.array(EntitlementFeatureSchema).catch([]),
});
export type Entitlements = z.infer<typeof EntitlementsSchema>;

export const emptyEntitlements = (): Entitlements => ({
  tier: "free",
  is_subscribed: false,
  subscription_end: null,
  limits: { analyses: { used: 0, allowed: 1, unlimited: false, remaining: 1 }, photos: 0 },
  features: [],
});

export const CoachSchema = z.object({
  date: z.string().catch(""),
  tier: z.string().catch("pro"),
  message: z.string().catch(""),
  focus: z.string().nullable().catch(null),
  tasks: z.array(z.string()).catch([]),
  score_context: z.string().catch(""),
  source: z.string().catch("template"),
});
export type Coach = z.infer<typeof CoachSchema>;

export const ReportCategorySchema = z.object({
  key: z.string().catch(""),
  score: z.number().catch(0),
  label: z.string().catch(""),
});
export const ReportSchema = z.object({
  photo_id: z.string().catch(""),
  overall_score: z.number().nullable().catch(null),
  potential_score: z.number().nullable().catch(null),
  improvement_gap: z.number().nullable().catch(null),
  face_shape: z.string().nullable().catch(null),
  categories: z.array(ReportCategorySchema).catch([]),
  weakest_areas: z.array(z.string()).catch([]),
  strongest_areas: z.array(z.string()).catch([]),
  strengths: z.array(z.string()).catch([]),
  weaknesses: z.array(z.string()).catch([]),
  improvement_potential: z.string().catch(""),
  recommendations: z
    .object({
      skincare: z.array(z.string()).catch([]),
      grooming: z.string().catch(""),
      exercise: z.array(z.string()).catch([]),
      diet: z.array(z.string()).catch([]),
    })
    .catch({ skincare: [], grooming: "", exercise: [], diet: [] }),
});
export type Report = z.infer<typeof ReportSchema>;

export const CheckoutSchema = z.object({
  checkout_url: z.string().nullable().catch(null),
});
export type Checkout = z.infer<typeof CheckoutSchema>;

// ── Premium insights (Pro) ──────────────────────────────────────────
export const ForecastMilestoneSchema = z.object({
  day: z.number().catch(0),
  projected_score: z.number().catch(0),
});
export const ForecastSchema = z.object({
  current_score: z.number().catch(0),
  potential_score: z.number().catch(0),
  days_remaining: z.number().catch(0),
  headline: z.string().catch(""),
  milestones: z.array(ForecastMilestoneSchema).catch([]),
});
export const PercentileSchema = z.object({
  percentile: z.number().nullable().catch(null),
  peer_count: z.number().catch(0),
  gender: z.string().catch(""),
  rank_label: z.string().catch(""),
});
export const ArchetypeSchema = z.object({
  name: z.string().catch(""),
  emoji: z.string().catch(""),
  vibe: z.string().catch(""),
  reasons: z.array(z.string()).catch([]),
});
export const InsightsSchema = z.object({
  photo_id: z.string().catch(""),
  forecast: ForecastSchema,
  percentile: PercentileSchema,
  archetype: ArchetypeSchema,
});
export type Insights = z.infer<typeof InsightsSchema>;
export const emptyInsights = (photoId: string): Insights => ({
  photo_id: photoId,
  forecast: { current_score: 0, potential_score: 0, days_remaining: 0, headline: "", milestones: [] },
  percentile: { percentile: null, peer_count: 0, gender: "", rank_label: "" },
  archetype: { name: "", emoji: "", vibe: "", reasons: [] },
});

// ── Premium harmony (Elite) ─────────────────────────────────────────
export const HarmonyMetricSchema = z.object({
  key: z.string().catch(""),
  label: z.string().catch(""),
  score: z.number().catch(0),
  alignment: z.number().catch(0),
});
export const GoldenRatioSchema = z.object({
  phi_score: z.number().nullable().catch(null),
  summary: z.string().catch(""),
  metrics: z.array(HarmonyMetricSchema).catch([]),
});
export const BlueprintDaySchema = z.object({
  day: z.number().catch(0),
  focus: z.string().catch(""),
  task: z.string().catch(""),
  why: z.string().catch(""),
  duration_minutes: z.number().catch(2),
});
export const BlueprintSchema = z.object({
  week_label: z.string().catch(""),
  gender_note: z.string().catch(""),
  days: z.array(BlueprintDaySchema).catch([]),
});
export const GlowUpCardSchema = z.object({
  headline: z.string().catch(""),
  score: z.number().catch(0),
  label: z.string().catch(""),
  archetype: z.string().catch(""),
  top_strength: z.string().catch(""),
  day: z.number().catch(0),
  tier: z.string().catch(""),
  share_text: z.string().catch(""),
});
export const HarmonySchema = z.object({
  photo_id: z.string().catch(""),
  golden_ratio: GoldenRatioSchema,
  blueprint: BlueprintSchema,
  glow_up_card: GlowUpCardSchema,
});
export type Harmony = z.infer<typeof HarmonySchema>;
export const emptyHarmony = (photoId: string): Harmony => ({
  photo_id: photoId,
  golden_ratio: { phi_score: null, summary: "", metrics: [] },
  blueprint: { week_label: "", gender_note: "", days: [] },
  glow_up_card: { headline: "", score: 0, label: "", archetype: "", top_strength: "", day: 0, tier: "", share_text: "" },
});

// ── Latest photo (for the Glow-Up page) ─────────────────────────────
export const LatestPhotoSchema = z.object({
  id: z.string().catch(""),
  file_url: z.string().catch(""),
  score: z.number().nullable().catch(null),
  is_baseline: z.boolean().catch(false),
  week_number: z.number().catch(1),
  captured_at: z.string().nullable().catch(null),
});
export type LatestPhoto = z.infer<typeof LatestPhotoSchema>;

// ── Momentum: Glow (daily reveal) ────────────────────────────────────
export const GlowStateSchema = z.object({
  journey_day: z.number().catch(1),
  glow_streak: z.number().catch(0),
  longest_glow_streak: z.number().catch(0),
  opens_count: z.number().catch(0),
  blur_next: z.number().catch(24),
  full_reveal: z.object({
    eligible: z.boolean().catch(false),
    unlocked: z.boolean().catch(false),
  }).catch({ eligible: false, unlocked: false }),
  weights: z.object({
    common: z.number().catch(0),
    rare: z.number().catch(0),
    epic: z.number().catch(0),
    legendary: z.number().catch(0),
  }).catch({ common: 70, rare: 24, epic: 5, legendary: 1 }),
});

export const GlowPayloadSchema = z.object({
  kind: z.string().catch(""),
  emoji: z.string().catch(""),
  headline: z.string().catch(""),
  body: z.string().catch(""),
  photo_url: z.string().nullable().catch(null),
  blur_px: z.number().nullable().catch(null),
  before_url: z.string().nullable().catch(null),
  after_url: z.string().nullable().catch(null),
  before_score: z.number().nullable().catch(null),
  after_score: z.number().nullable().catch(null),
  delta: z.number().nullable().catch(null),
  share_text: z.string().nullable().catch(null),
});

export const GlowRevealSchema = z.object({
  id: z.string().catch(""),
  day: z.number().catch(1),
  rarity: z.string().catch("common"),
  reward_type: z.string().catch("micro_win"),
  payload: GlowPayloadSchema.catch({
    kind: "", emoji: "", headline: "", body: "", photo_url: null, blur_px: null,
    before_url: null, after_url: null, before_score: null, after_score: null,
    delta: null, share_text: null,
  }),
  opened_at: z.string().nullable().catch(null),
});

export const GlowStateResponseSchema = z.object({
  can_open: z.boolean().catch(false),
  opened_today: z.boolean().catch(false),
  today_reveal: GlowRevealSchema.nullable().catch(null),
  state: GlowStateSchema,
});
export const GlowOpenResponseSchema = z.object({
  already_opened: z.boolean().catch(false),
  reveal: GlowRevealSchema,
  state: GlowStateSchema,
});
export const GlowRevealsResponseSchema = z.object({
  reveals: z.array(GlowRevealSchema).catch([]),
  total: z.number().catch(0),
});
export type GlowState = z.infer<typeof GlowStateSchema>;
export type GlowReveal = z.infer<typeof GlowRevealSchema>;
export type GlowStateResponse = z.infer<typeof GlowStateResponseSchema>;
export type GlowOpenResponse = z.infer<typeof GlowOpenResponseSchema>;

// ── Momentum: The Arc (XP / levels / quests / badges) ────────────────
export const ArcQuestSchema = z.object({
  id: z.string().catch(""),
  focus: z.string().catch(""),
  task: z.string().catch(""),
  why: z.string().catch(""),
  xp: z.number().catch(0),
  claimed: z.boolean().catch(false),
  locked: z.boolean().catch(true),
});
export const ArcBadgeSchema = z.object({
  badge_key: z.string().catch(""),
  name: z.string().catch(""),
  emoji: z.string().catch("🏅"),
  description: z.string().catch(""),
  unlocked_at: z.string().nullable().catch(null),
});
export const ArcSkillNodeSchema = z.object({
  key: z.string().catch(""),
  name: z.string().catch(""),
  emoji: z.string().catch(""),
  unlocked: z.boolean().catch(false),
});
export const ArcStateSchema = z.object({
  level: z.number().catch(1),
  total_xp: z.number().catch(0),
  xp_to_next: z.number().catch(100),
  title: z.string().catch(""),
  archetype: z.string().catch("Rookie"),
  milestone_title: z.string().nullable().catch(null),
  premium: z.boolean().catch(false),
  today_quests: z.array(ArcQuestSchema).catch([]),
  badges: z.array(ArcBadgeSchema).catch([]),
  skill_tree: z.array(ArcSkillNodeSchema).catch([]),
});
export const ArcClaimSchema = z.object({
  xp_awarded: z.number().catch(0),
  level: z.number().catch(1),
  total_xp: z.number().catch(0),
  leveled_up: z.boolean().catch(false),
  new_title: z.string().nullable().catch(null),
});
export type ArcState = z.infer<typeof ArcStateSchema>;
export type ArcClaim = z.infer<typeof ArcClaimSchema>;
export type ArcQuest = z.infer<typeof ArcQuestSchema>;
export type ArcBadge = z.infer<typeof ArcBadgeSchema>;

// ── Momentum: Glow-Ups (feed + movie) ────────────────────────────────
export const GlowupFeedItemSchema = z.object({
  id: z.string().catch(""),
  first_name: z.string().catch(""),
  age: z.number().nullable().catch(null),
  day: z.number().catch(1),
  delta: z.number().catch(0),
  headline: z.string().catch(""),
  cover_url: z.string().nullable().catch(null),
  blur: z.boolean().catch(true),
  seed: z.boolean().catch(false),
});
export const GlowupFeedSchema = z.object({
  items: z.array(GlowupFeedItemSchema).catch([]),
  next_cursor: z.number().nullable().catch(null),
  locked: z.boolean().catch(false),
});
export const GlowupConsentSchema = z.object({
  share_enabled: z.boolean().catch(false),
  error: z.string().nullable().catch(null),
});
export const GlowupMovieSchema = z.object({
  status: z.string().catch("pending"),
  trailers: z.array(z.object({
    day: z.number().catch(0),
    title: z.string().catch(""),
    photo_urls: z.array(z.string()).catch([]),
  })).catch([]),
  full_movie_url: z.string().nullable().catch(null),
  photo_urls: z.array(z.string()).catch([]),
  delta: z.number().catch(0),
});
export type GlowupFeedItem = z.infer<typeof GlowupFeedItemSchema>;
export type GlowupFeed = z.infer<typeof GlowupFeedSchema>;
export type GlowupConsent = z.infer<typeof GlowupConsentSchema>;
export type GlowupMovie = z.infer<typeof GlowupMovieSchema>;

export type DeleteAccountResult = z.infer<typeof DeleteAccountSchema>;





