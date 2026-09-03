"use client";

import { useQuery } from "@tanstack/react-query";
import { getAdminFunnel, getAdminOverview } from "@/lib/api/admin";
import { Card, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Skeleton";

export default function AdminDashboard() {
  const overview = useQuery({ queryKey: ["admin-overview"], queryFn: getAdminOverview });
  const funnel = useQuery({ queryKey: ["admin-funnel"], queryFn: getAdminFunnel });

  const o = overview.data;
  const f = funnel.data ?? [];

  if (overview.isLoading) {
    return (
      <div className="flex justify-center py-20">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  const kpis = [
    { label: "Total users", value: o?.users.total ?? 0 },
    { label: "New (24h)", value: o?.users.new_24h ?? 0 },
    { label: "New (7d)", value: o?.users.new_7d ?? 0 },
    { label: "DAU", value: o?.traffic.dau ?? 0 },
    { label: "WAU", value: o?.traffic.wau ?? 0 },
    { label: "MAU", value: o?.traffic.mau ?? 0 },
    { label: "Photos", value: o?.engagement.photos ?? 0 },
    { label: "Check-ins", value: o?.engagement.checkins ?? 0 },
    { label: "Plans", value: o?.engagement.plans ?? 0 },
    { label: "Pro", value: o?.monetization.pro ?? 0 },
    { label: "Elite", value: o?.monetization.elite ?? 0 },
    { label: "Sessions", value: o?.traffic.sessions ?? 0 },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Dashboard</h1>
        <p className="text-sm text-muted">High-level health of the business.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {kpis.map((k) => (
          <Card key={k.label} className="p-4">
            <div className="text-xs text-muted">{k.label}</div>
            <div className="mt-1 text-2xl font-semibold tabular text-ink">{k.value}</div>
          </Card>
        ))}
      </div>

      <Card>
        <CardTitle className="mb-4">Conversion funnel</CardTitle>
        <div className="space-y-2">
          {f.map((stage) => (
            <div key={stage.stage} className="flex items-center gap-3">
              <div className="w-24 text-sm capitalize text-muted">{stage.stage}</div>
              <div className="h-8 flex-1 overflow-hidden rounded-lg bg-surface-2">
                <div
                  className="gold-gradient h-full"
                  style={{ width: `${Math.min(100, stage.of_signup)}%` }}
                />
              </div>
              <div className="w-24 text-right text-sm tabular text-ink">
                {stage.count}
                <span className="ml-1 text-xs text-muted">
                  {stage.conversion_from_previous != null
                    ? `${stage.conversion_from_previous}%`
                    : "—"}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <CardTitle className="mb-3">Traffic</CardTitle>
        <div className="flex flex-wrap gap-2">
          <Badge variant="muted">Events: {o?.traffic.total_events ?? 0}</Badge>
          <Badge variant="muted">
            Avg session: {o?.traffic.avg_session_sec != null ? `${o.traffic.avg_session_sec}s` : "n/a"}
          </Badge>
        </div>
      </Card>
    </div>
  );
}
