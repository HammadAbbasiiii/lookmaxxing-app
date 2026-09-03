"use client";

import { useQuery } from "@tanstack/react-query";
import { getAdminActivity } from "@/lib/api/admin";
import { Card, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Skeleton";

export default function AdminActivity() {
  const activity = useQuery({ queryKey: ["admin-activity"], queryFn: () => getAdminActivity(200, 0) });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Activity</h1>
        <p className="text-sm text-muted">Audit log of every admin action.</p>
      </div>

      <Card>
        <CardTitle className="mb-4">Audit log</CardTitle>
        {activity.isLoading ? (
          <div className="flex justify-center py-10">
            <Spinner className="h-6 w-6" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-soft text-left text-muted">
                  <th className="py-2 pr-4 font-medium">When</th>
                  <th className="py-2 pr-4 font-medium">Admin</th>
                  <th className="py-2 pr-4 font-medium">Action</th>
                  <th className="py-2 pr-4 font-medium">Entity</th>
                  <th className="py-2 font-medium">Details</th>
                </tr>
              </thead>
              <tbody>
                {activity.data?.actions.map((a) => (
                  <tr key={a.id} className="border-b border-border-soft/50">
                    <td className="py-2 pr-4 text-muted">
                      {a.created_at ? new Date(a.created_at).toLocaleString() : "—"}
                    </td>
                    <td className="py-2 pr-4 text-ink">{a.admin_email}</td>
                    <td className="py-2 pr-4">
                      <Badge variant={a.action === "delete" ? "danger" : "gold"}>{a.action}</Badge>
                    </td>
                    <td className="py-2 pr-4 text-ink">
                      {a.entity_type}
                      {a.entity_id ? ` · ${a.entity_id}` : ""}
                    </td>
                    <td className="py-2 text-muted">
                      {a.details ? JSON.stringify(a.details) : "—"}
                    </td>
                  </tr>
                ))}
                {activity.data && activity.data.actions.length === 0 && (
                  <tr>
                    <td className="py-6 text-center text-muted" colSpan={5}>
                      No admin actions yet.
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
