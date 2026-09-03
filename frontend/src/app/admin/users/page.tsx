"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getAdminUsers, setUserAdmin, setUserTier } from "@/lib/api/admin";
import { useMe } from "@/hooks/useMe";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Skeleton";

export default function AdminUsers() {
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const qc = useQueryClient();
  const { data: me } = useMe();

  const users = useQuery({
    queryKey: ["admin-users", q],
    queryFn: () => getAdminUsers(q || undefined, 200, 0),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["admin-users"] });
    qc.invalidateQueries({ queryKey: ["admin-user"] });
    qc.invalidateQueries({ queryKey: ["me"] });
  };

  const setAdmin = useMutation({
    mutationFn: ({ id, isAdmin }: { id: string; isAdmin: boolean }) => setUserAdmin(id, isAdmin),
    onSuccess: (res, vars) => {
      toast.success(vars.isAdmin ? `${res.email} is now an admin` : `${res.email} admin access revoked`);
      invalidate();
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Failed to update admin status"),
  });

  const setTier = useMutation({
    mutationFn: ({ id, tier }: { id: string; tier: string }) => setUserTier(id, tier),
    onSuccess: (res) => {
      toast.success(`${res.email} tier set to ${res.tier}`);
      invalidate();
    },
    onError: (e) => toast.error(e instanceof Error ? e.message : "Failed to update tier"),
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-ink">Users</h1>
        <p className="text-sm text-muted">Search by email and open any user for a full 360° view.</p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setQ(search.trim());
        }}
        className="flex gap-2"
      >
        <Input
          id="user-search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by email…"
          className="max-w-sm"
        />
        <Button type="submit" variant="secondary" size="sm">
          Search
        </Button>
      </form>

      <Card>
        {users.isLoading ? (
          <div className="flex justify-center py-10">
            <Spinner className="h-6 w-6" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-soft text-left text-muted">
                  <th className="py-2 pr-4 font-medium">Email</th>
                  <th className="py-2 pr-4 font-medium">Tier</th>
                  <th className="py-2 pr-4 font-medium">Admin</th>
                  <th className="py-2 pr-4 font-medium">Day</th>
                  <th className="py-2 pr-4 font-medium">Streak</th>
                  <th className="py-2 pr-4 font-medium">Check-ins</th>
                  <th className="py-2 pr-4 font-medium">Events</th>
                  <th className="py-2 font-medium">Last seen</th>
                </tr>
              </thead>
              <tbody>
                {users.data?.users.map((u) => (
                  <tr key={u.id} className="border-b border-border-soft/50">
                    <td className="py-2 pr-4">
                      <Link href={`/admin/users/${u.id}`} className="text-gold hover:underline">
                        {u.email}
                      </Link>
                    </td>
                    <td className="py-2 pr-4">
                      <select
                        value={u.tier}
                        disabled={setTier.isPending}
                        onChange={(e) => setTier.mutate({ id: u.id, tier: e.target.value })}
                        className="rounded-lg border border-border-soft bg-surface px-2 py-1 text-sm text-ink"
                      >
                        <option value="free">free</option>
                        <option value="pro">pro</option>
                        <option value="elite">elite</option>
                      </select>
                    </td>
                    <td className="py-2 pr-4">
                      {u.id === me?.id ? (
                        <Badge variant={u.is_admin ? "gold" : "muted"}>
                          {u.is_admin ? "Admin (you)" : "you"}
                        </Badge>
                      ) : u.is_admin ? (
                        <Button
                          variant="danger"
                          size="sm"
                          disabled={setAdmin.isPending}
                          onClick={() => setAdmin.mutate({ id: u.id, isAdmin: false })}
                        >
                          Revoke
                        </Button>
                      ) : (
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={setAdmin.isPending}
                          onClick={() => setAdmin.mutate({ id: u.id, isAdmin: true })}
                        >
                          Make admin
                        </Button>
                      )}
                    </td>
                    <td className="py-2 pr-4 tabular text-ink">{u.current_day}</td>
                    <td className="py-2 pr-4 tabular text-ink">{u.current_streak}</td>
                    <td className="py-2 pr-4 tabular text-ink">{u.total_checkins}</td>
                    <td className="py-2 pr-4 tabular text-ink">{u.event_count}</td>
                    <td className="py-2 text-muted">
                      {u.last_seen ? new Date(u.last_seen).toLocaleDateString() : "never"}
                    </td>
                  </tr>
                ))}
                {users.data && users.data.users.length === 0 && (
                  <tr>
                    <td className="py-6 text-center text-muted" colSpan={8}>
                      No users found.
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
