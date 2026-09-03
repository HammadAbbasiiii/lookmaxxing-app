"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getAdminUserDetail, setUserAdmin, setUserTier } from "@/lib/api/admin";
import { Card, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";

const s = (v: unknown): string => (typeof v === "string" ? v : "");
const n = (v: unknown): number | null => (typeof v === "number" && Number.isFinite(v) ? v : null);

export default function AdminUserDetail() {
  const params = useParams<{ id: string }>();
  const id = params?.id ?? "";

  const detail = useQuery({
    queryKey: ["admin-user", id],
    queryFn: () => getAdminUserDetail(id),
    enabled: Boolean(id),
  });

  const qc = useQueryClient();
  const isTargetAdmin = detail.data?.user?.is_admin === true;
  const targetTier = s(detail.data?.user?.tier) || "free";

  const mutateAdmin = useMutation({
    mutationFn: (isAdmin: boolean) => setUserAdmin(id, isAdmin),
    onSuccess: (res, isAdmin) => {
      toast.success(isAdmin ? `${res.email} is now an admin` : `${res.email} admin access revoked`);
      qc.invalidateQueries({ queryKey: ["admin-user", id] });
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      qc.invalidateQueries({ queryKey: ["me"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Failed to update admin status"),
  });

  const mutateTier = useMutation({
    mutationFn: (tier: string) => setUserTier(id, tier),
    onSuccess: (res) => {
      toast.success(`${res.email} tier set to ${res.tier}`);
      qc.invalidateQueries({ queryKey: ["admin-user", id] });
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      qc.invalidateQueries({ queryKey: ["me"] });
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Failed to update tier"),
  });

  if (detail.isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  const d = detail.data;
  if (!d) return null;

  const user = d.user;
  const profile = d.profile;
  const analytics = d.analytics;
  const pages = (analytics.pages && typeof analytics.pages === "object"
    ? (analytics.pages as Record<string, unknown>)
    : {}) as Record<string, unknown>;

  const stage = s(profile.funnel_stage);
  const stageVariant =
    stage === "paid" || stage === "at_checkout" ? "success" : stage === "at_paywall" ? "warning" : "muted";

  const facts: Array<[string, unknown]> = [
    ["Email", s(user.email)],
    ["Tier", s(user.tier)],
    ["Admin", user.is_admin === true ? "Yes" : "No"],
    ["Onboarding complete", user.onboarding_completed === true ? "Yes" : "No"],
    ["Account created", user.created_at ? new Date(s(user.created_at)).toLocaleString() : "—"],
    ["Plan day", `${n(user.current_day) ?? 0} / 90`],
    ["Current streak", n(user.current_streak) ?? 0],
    ["Longest streak", n(user.longest_streak) ?? 0],
    ["Total check-ins", n(user.total_checkins) ?? 0],
  ];

  const profileRows: Array<[string, unknown]> = [
    ["Photos uploaded", profile.photos_uploaded],
    ["Photos analyzed", profile.photos_analyzed],
    ["Baseline score", profile.baseline_score],
    ["Latest score", profile.latest_score],
    ["Score delta", profile.score_delta],
    ["Photos viewed", profile.photos_viewed],
    ["Products viewed/clicked", profile.products_viewed],
    ["Pricing page views", profile.pricing_viewed],
    ["Upgrade clicks", profile.upgrade_clicks],
    ["Checkout started", profile.checkout_started],
    ["Checkout completed", profile.checkout_completed],
    ["Sessions", profile.session_count],
    ["Total time (sec)", analytics.total_time_sec],
    ["Last page (exit)", profile.last_page],
  ];

  const recentEvents = Array.isArray(analytics.recent_events)
    ? (analytics.recent_events as Record<string, unknown>[])
    : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link href="/admin/users" className="text-sm text-muted hover:text-ink">
          ← Users
        </Link>
        <h1 className="text-2xl font-semibold text-ink">{s(user.email)}</h1>
        <Badge variant={stageVariant as "success" | "warning" | "muted"}>{stage}</Badge>
      </div>

      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <CardTitle className="mb-0 mr-2">Manage user</CardTitle>
          <Button
            variant={isTargetAdmin ? "danger" : "secondary"}
            size="sm"
            disabled={mutateAdmin.isPending}
            onClick={() => mutateAdmin.mutate(!isTargetAdmin)}
          >
            {isTargetAdmin ? "Revoke admin" : "Make admin"}
          </Button>
          <label className="flex items-center gap-2 text-sm text-muted">
            Tier
            <select
              value={targetTier}
              disabled={mutateTier.isPending}
              onChange={(e) => mutateTier.mutate(e.target.value)}
              className="rounded-lg border border-border-soft bg-surface px-2 py-1 text-sm text-ink"
            >
              <option value="free">free</option>
              <option value="pro">pro</option>
              <option value="elite">elite</option>
            </select>
          </label>
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardTitle className="mb-3">Account</CardTitle>
          <dl className="space-y-2 text-sm">
            {facts.map(([label, value]) => (
              <div key={label} className="flex justify-between gap-4">
                <dt className="text-muted">{label}</dt>
                <dd className="text-ink">{String(value ?? "—")}</dd>
              </div>
            ))}
          </dl>
        </Card>

        <Card>
          <CardTitle className="mb-3">User 360 (tracked activity)</CardTitle>
          <dl className="space-y-2 text-sm">
            {profileRows.map(([label, value]) => (
              <div key={label} className="flex justify-between gap-4">
                <dt className="text-muted">{label}</dt>
                <dd className="text-ink">{value != null && value !== "" ? String(value) : "—"}</dd>
              </div>
            ))}
          </dl>
        </Card>
      </div>

      <Card>
        <CardTitle className="mb-3">Top pages</CardTitle>
        {Object.keys(pages).length === 0 ? (
          <p className="text-sm text-muted">No page views recorded.</p>
        ) : (
          <div className="space-y-1 text-sm">
            {Object.entries(pages)
              .sort((a, b) => Number(b[1]) - Number(a[1]))
              .slice(0, 10)
              .map(([page, count]) => (
                <div key={page} className="flex justify-between gap-4">
                  <span className="text-ink">{page}</span>
                  <span className="tabular text-muted">{String(count)}</span>
                </div>
              ))}
          </div>
        )}
      </Card>

      <Card>
        <CardTitle className="mb-3">Recent events</CardTitle>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-soft text-left text-muted">
                <th className="py-2 pr-4 font-medium">Event</th>
                <th className="py-2 pr-4 font-medium">Page</th>
                <th className="py-2 font-medium">When</th>
              </tr>
            </thead>
            <tbody>
              {recentEvents.map((e, i) => (
                <tr key={i} className="border-b border-border-soft/50">
                  <td className="py-2 pr-4 text-ink">{s(e.event)}</td>
                  <td className="py-2 pr-4 text-ink">{s(e.page) || "—"}</td>
                  <td className="py-2 text-muted">
                    {e.at ? new Date(s(e.at)).toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
              {recentEvents.length === 0 && (
                <tr>
                  <td className="py-4 text-center text-muted" colSpan={3}>
                    No events recorded.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

