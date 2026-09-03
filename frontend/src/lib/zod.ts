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
  onboarding_completed: z.boolean().catch(false),
  subscription_tier: z.string().catch("free"),
  is_subscribed: z.boolean().catch(false),
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
  onboarding_completed: false,
  subscription_tier: "free",
  is_subscribed: false,
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
export type DeleteAccountResult = z.infer<typeof DeleteAccountSchema>;





