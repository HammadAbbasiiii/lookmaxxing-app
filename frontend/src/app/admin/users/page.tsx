"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getAdminUsers } from "@/lib/api/admin";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Skeleton";

export default function AdminUsers() {
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");

  const users = useQuery({
    queryKey: ["admin-users", q],
    queryFn: () => getAdminUsers(q || undefined, 200, 0),
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
                      <Badge variant={u.tier === "free" ? "muted" : "gold"}>{u.tier}</Badge>
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
                    <td className="py-6 text-center text-muted" colSpan={7}>
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
