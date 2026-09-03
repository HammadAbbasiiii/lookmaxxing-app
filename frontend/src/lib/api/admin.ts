// Admin API client — owner dashboard. Defensive parsing mirrors the rest of
// the API layer: a malformed payload never throws into the UI.

import { apiFetch } from "@/lib/api/client";

const s = (v: unknown): string => (typeof v === "string" ? v : "");
const n = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);
const n0 = (v: unknown): number => (typeof v === "number" && Number.isFinite(v) ? v : 0);
const arr = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
const rec = (v: unknown): Record<string, unknown> =>
  v && typeof v === "object" ? (v as Record<string, unknown>) : {};
const iso = (v: unknown): string | null => (typeof v === "string" ? v : null);

// ── Types ────────────────────────────────────────────────────────────
export interface AdminOverview {
  users: { total: number; new_24h: number; new_7d: number; new_30d: number };
  engagement: { photos: number; checkins: number; plans: number };
  monetization: { pro: number; elite: number };
  traffic: {
    total_events: number;
    sessions: number;
    dau: number;
    wau: number;
    mau: number;
    avg_session_sec: number | null;
  };
}

export interface AdminUserRow {
  id: string;
  email: string;
  tier: string;
  is_admin: boolean;
  created_at: string | null;
  current_day: number;
  current_streak: number;
  total_checkins: number;
  event_count: number;
  last_seen: string | null;
}

export interface AdminProduct {
  id: string;
  name: string;
  brand: string | null;
  category: string;
  price: number | null;
  currency: string;
  tier: string;
  image_url: string | null;
  affiliate_url: string | null;
  description: string | null;
  rating: number | null;
  review_count: number;
  social_proof: string | null;
  commission: number | null;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface FunnelStage {
  stage: string;
  count: number;
  conversion_from_previous: number | null;
  of_signup: number;
}

export interface RetentionCohort {
  week: string;
  users: number;
  w0: number;
  w1: number;
  w2: number;
  w3: number;
}

export interface AdminEvent {
  id: string;
  user_id: string | null;
  event: string;
  page: string | null;
  referrer: string | null;
  properties: Record<string, unknown> | null;
  created_at: string | null;
}

export interface AdminActionRow {
  id: string;
  admin_email: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string | null;
}

export interface AdminUserDetail {
  user: Record<string, unknown>;
  photos: Record<string, unknown>[];
  plans: Record<string, unknown>[];
  checkins: Record<string, unknown>[];
  analytics: Record<string, unknown>;
  profile: Record<string, unknown>;
}

// ── Overview ─────────────────────────────────────────────────────────
export async function getAdminOverview(): Promise<AdminOverview> {
  const data = await apiFetch<unknown>("/admin/overview");
  const r = rec(data);
  const users = rec(r.users);
  const engagement = rec(r.engagement);
  const monetization = rec(r.monetization);
  const traffic = rec(r.traffic);
  return {
    users: {
      total: n0(users.total),
      new_24h: n0(users.new_24h),
      new_7d: n0(users.new_7d),
      new_30d: n0(users.new_30d),
    },
    engagement: {
      photos: n0(engagement.photos),
      checkins: n0(engagement.checkins),
      plans: n0(engagement.plans),
    },
    monetization: { pro: n0(monetization.pro), elite: n0(monetization.elite) },
    traffic: {
      total_events: n0(traffic.total_events),
      sessions: n0(traffic.sessions),
      dau: n0(traffic.dau),
      wau: n0(traffic.wau),
      mau: n0(traffic.mau),
      avg_session_sec: n(traffic.avg_session_sec),
    },
  };
}

// ── Users ────────────────────────────────────────────────────────────
export async function getAdminUsers(
  search?: string,
  limit = 50,
  offset = 0,
): Promise<{ total: number; users: AdminUserRow[] }> {
  const qs = new URLSearchParams();
  if (search) qs.set("search", search);
  qs.set("limit", String(limit));
  qs.set("offset", String(offset));
  const data = await apiFetch<unknown>(`/admin/users?${qs.toString()}`);
  const r = rec(data);
  const users = arr(r.users).map((u) => {
    const w = rec(u);
    return {
      id: s(w.id),
      email: s(w.email),
      tier: s(w.tier),
      is_admin: w.is_admin === true,
      created_at: iso(w.created_at),
      current_day: n0(w.current_day),
      current_streak: n0(w.current_streak),
      total_checkins: n0(w.total_checkins),
      event_count: n0(w.event_count),
      last_seen: iso(w.last_seen),
    } satisfies AdminUserRow;
  });
  return { total: n0(r.total), users };
}

export async function getAdminUserDetail(id: string): Promise<AdminUserDetail> {
  const data = await apiFetch<unknown>(`/admin/users/${encodeURIComponent(id)}`);
  const r = rec(data);
  return {
    user: rec(r.user),
    photos: arr(r.photos).map(rec),
    plans: arr(r.plans).map(rec),
    checkins: arr(r.checkins).map(rec),
    analytics: rec(r.analytics),
    profile: rec(r.profile),
  };
}

export async function setUserAdmin(
  id: string,
  isAdmin: boolean,
): Promise<{ id: string; email: string; is_admin: boolean }> {
  const data = await apiFetch<unknown>(`/admin/users/${encodeURIComponent(id)}/admin`, {
    method: "PATCH",
    body: { is_admin: isAdmin },
  });
  const w = rec(rec(data).user);
  return { id: s(w.id), email: s(w.email), is_admin: w.is_admin === true };
}

export async function setUserTier(
  id: string,
  tier: string,
): Promise<{ id: string; email: string; tier: string }> {
  const data = await apiFetch<unknown>(`/admin/users/${encodeURIComponent(id)}/tier`, {
    method: "PATCH",
    body: { tier },
  });
  const w = rec(rec(data).user);
  return { id: s(w.id), email: s(w.email), tier: s(w.tier) };
}

// ── Funnel / retention / events ──────────────────────────────────────
export async function getAdminFunnel(): Promise<FunnelStage[]> {
  const data = await apiFetch<unknown>("/admin/funnel");
  return arr(rec(data).funnel).map((f) => {
    const w = rec(f);
    return {
      stage: s(w.stage),
      count: n0(w.count),
      conversion_from_previous: n(w.conversion_from_previous),
      of_signup: n0(w.of_signup),
    };
  });
}

export async function getAdminRetention(weeks = 8): Promise<RetentionCohort[]> {
  const data = await apiFetch<unknown>(`/admin/retention?weeks=${weeks}`);
  return arr(rec(data).cohorts).map((c) => {
    const w = rec(c);
    return {
      week: s(w.week),
      users: n0(w.users),
      w0: n0(w.w0),
      w1: n0(w.w1),
      w2: n0(w.w2),
      w3: n0(w.w3),
    };
  });
}

export async function getAdminEvents(filters: {
  event_name?: string;
  user_id?: string;
  page?: string;
  start?: string;
  end?: string;
  limit?: number;
  offset?: number;
}): Promise<{ total: number; events: AdminEvent[] }> {
  const qs = new URLSearchParams();
  if (filters.event_name) qs.set("event_name", filters.event_name);
  if (filters.user_id) qs.set("user_id", filters.user_id);
  if (filters.page) qs.set("page", filters.page);
  if (filters.start) qs.set("start", filters.start);
  if (filters.end) qs.set("end", filters.end);
  qs.set("limit", String(filters.limit ?? 100));
  qs.set("offset", String(filters.offset ?? 0));
  const data = await apiFetch<unknown>(`/admin/events?${qs.toString()}`);
  const r = rec(data);
  const events = arr(r.events).map((e) => {
    const w = rec(e);
    return {
      id: s(w.id),
      user_id: iso(w.user_id),
      event: s(w.event),
      page: iso(w.page),
      referrer: iso(w.referrer),
      properties: w.properties && typeof w.properties === "object" ? (w.properties as Record<string, unknown>) : null,
      created_at: iso(w.created_at),
    } satisfies AdminEvent;
  });
  return { total: n0(r.total), events };
}

// ── Products (CRUD) ─────────────────────────────────────────────────
export async function getAdminProducts(params: {
  search?: string;
  category?: string;
  tier?: string;
  active?: boolean;
  limit?: number;
  offset?: number;
} = {}): Promise<{ total: number; products: AdminProduct[] }> {
  const qs = new URLSearchParams();
  if (params.search) qs.set("search", params.search);
  if (params.category) qs.set("category", params.category);
  if (params.tier) qs.set("tier", params.tier);
  if (params.active !== undefined) qs.set("active", String(params.active));
  qs.set("limit", String(params.limit ?? 100));
  qs.set("offset", String(params.offset ?? 0));
  const data = await apiFetch<unknown>(`/admin/products?${qs.toString()}`);
  const r = rec(data);
  const products = arr(r.products).map(parseProduct);
  return { total: n0(r.total), products };
}

export async function createProduct(payload: Record<string, unknown>): Promise<AdminProduct> {
  const data = await apiFetch<unknown>("/admin/products", { method: "POST", body: payload });
  return parseProduct(rec(data).product);
}

export async function updateProduct(id: string, payload: Record<string, unknown>): Promise<AdminProduct> {
  const data = await apiFetch<unknown>(`/admin/products/${encodeURIComponent(id)}`, {
    method: "PUT",
    body: payload,
  });
  return parseProduct(rec(data).product);
}

export async function deleteProduct(id: string): Promise<AdminProduct> {
  const data = await apiFetch<unknown>(`/admin/products/${encodeURIComponent(id)}`, { method: "DELETE" });
  return parseProduct(rec(data).product);
}

export async function activateProduct(id: string): Promise<AdminProduct> {
  const data = await apiFetch<unknown>(`/admin/products/${encodeURIComponent(id)}/activate`, {
    method: "POST",
  });
  return parseProduct(rec(data).product);
}

export async function importProducts(): Promise<{ created: number; updated: number }> {
  const data = await apiFetch<unknown>("/admin/products/import", { method: "POST" });
  const r = rec(data);
  return { created: n0(r.created), updated: n0(r.updated) };
}

function parseProduct(v: unknown): AdminProduct {
  const w = rec(v);
  return {
    id: s(w.id),
    name: s(w.name),
    brand: iso(w.brand),
    category: s(w.category),
    price: n(w.price),
    currency: s(w.currency),
    tier: s(w.tier),
    image_url: iso(w.image_url),
    affiliate_url: iso(w.affiliate_url),
    description: iso(w.description),
    rating: n(w.rating),
    review_count: n0(w.review_count),
    social_proof: iso(w.social_proof),
    commission: n(w.commission),
    is_active: w.is_active !== false,
    created_at: iso(w.created_at),
    updated_at: iso(w.updated_at),
  };
}

// ── Activity (audit log) ─────────────────────────────────────────────
export async function getAdminActivity(
  limit = 100,
  offset = 0,
): Promise<{ total: number; actions: AdminActionRow[] }> {
  const data = await apiFetch<unknown>(`/admin/activity?limit=${limit}&offset=${offset}`);
  const r = rec(data);
  const actions = arr(r.actions).map((a) => {
    const w = rec(a);
    return {
      id: s(w.id),
      admin_email: s(w.admin_email),
      action: s(w.action),
      entity_type: s(w.entity_type),
      entity_id: iso(w.entity_id),
      details: w.details && typeof w.details === "object" ? (w.details as Record<string, unknown>) : null,
      created_at: iso(w.created_at),
    } satisfies AdminActionRow;
  });
  return { total: n0(r.total), actions };
}


