"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAdminEvents, getAdminFunnel, getAdminRetention } from "@/lib/api/admin";
import { Card, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Skeleton";

export default function AdminAnalytics() {
  const funnel = useQuery({ queryKey: ["admin-funnel"], queryFn: getAdminFunnel });
  const retention = useQuery({ queryKey: ["admin-retention"], queryFn: () => getAdminRetention(8) });

  const [eventName, setEventName] = useState("");
  const [eventFilter, setEventFilter] = useState("");
  const events = useQuery({
    queryKey: ["admin-events", eventFilter],
    queryFn: () => getAdminEvents({ event_name: eventFilter || undefined, limit: 200 }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Analytics</h1>
        <p className="text-sm text-muted">Conversion funnel, cohort retention and the raw event stream.</p>
      </div>

      <Card>
        <CardTitle className="mb-4">Conversion funnel</CardTitle>
        {funnel.isLoading ? (
          <Spinner className="h-6 w-6" />
        ) : (
          <div className="space-y-2">
            {funnel.data?.map((stage) => (
              <div key={stage.stage} className="flex items-center gap-3">
                <div className="w-24 text-sm capitalize text-muted">{stage.stage}</div>
                <div className="h-8 flex-1 overflow-hidden rounded-lg bg-surface-2">
                  <div
                    className="gold-gradient h-full"
                    style={{ width: `${Math.min(100, stage.of_signup)}%` }}
                  />
                </div>
                <div className="w-28 text-right text-sm tabular text-ink">
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
        )}
      </Card>

      <Card>
        <CardTitle className="mb-4">Weekly cohort retention (%)</CardTitle>
        {retention.isLoading ? (
          <Spinner className="h-6 w-6" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-soft text-left text-muted">
                  <th className="py-2 pr-4 font-medium">Cohort</th>
                  <th className="py-2 pr-4 font-medium">Users</th>
                  <th className="py-2 pr-4 font-medium">W0</th>
                  <th className="py-2 pr-4 font-medium">W1</th>
                  <th className="py-2 pr-4 font-medium">W2</th>
                  <th className="py-2 font-medium">W3</th>
                </tr>
              </thead>
              <tbody>
                {retention.data?.map((c) => (
                  <tr key={c.week} className="border-b border-border-soft/50">
                    <td className="py-2 pr-4 text-ink">{c.week}</td>
                    <td className="py-2 pr-4 tabular text-ink">{c.users}</td>
                    <td className="py-2 pr-4 tabular text-ink">{c.w0}%</td>
                    <td className="py-2 pr-4 tabular text-ink">{c.w1}%</td>
                    <td className="py-2 pr-4 tabular text-ink">{c.w2}%</td>
                    <td className="py-2 tabular text-ink">{c.w3}%</td>
                  </tr>
                ))}
                {retention.data && retention.data.length === 0 && (
                  <tr>
                    <td className="py-4 text-center text-muted" colSpan={6}>
                      No retention data yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card>
        <CardTitle className="mb-4">Event explorer</CardTitle>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setEventFilter(eventName.trim());
          }}
          className="mb-4 flex gap-2"
        >
          <Input
            id="event-filter"
            value={eventName}
            onChange={(e) => setEventName(e.target.value)}
            placeholder="Filter by event name…"
            className="max-w-xs"
          />
          <Button type="submit" variant="secondary" size="sm">
            Filter
          </Button>
        </form>

        {events.isLoading ? (
          <Spinner className="h-6 w-6" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-soft text-left text-muted">
                  <th className="py-2 pr-4 font-medium">Event</th>
                  <th className="py-2 pr-4 font-medium">Page</th>
                  <th className="py-2 pr-4 font-medium">User</th>
                  <th className="py-2 font-medium">When</th>
                </tr>
              </thead>
              <tbody>
                {events.data?.events.map((e) => (
                  <tr key={e.id} className="border-b border-border-soft/50">
                    <td className="py-2 pr-4 text-ink">{e.event}</td>
                    <td className="py-2 pr-4 text-muted">{e.page || "—"}</td>
                    <td className="py-2 pr-4 text-muted">{e.user_id || "anonymous"}</td>
                    <td className="py-2 text-muted">
                      {e.created_at ? new Date(e.created_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
                {events.data && events.data.events.length === 0 && (
                  <tr>
                    <td className="py-4 text-center text-muted" colSpan={4}>
                      No events.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

