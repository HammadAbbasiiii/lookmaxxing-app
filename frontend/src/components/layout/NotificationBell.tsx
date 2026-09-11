"use client";

import { Bell } from "lucide-react";

/**
 * Notification bell (top-right, next to avatar).
 *
 * NOTE: There is no notifications feature in the backend yet, so this is a
 * visual placeholder. Wire it up to a `/notifications` route or a polling
 * endpoint once notifications land.
 */
export function NotificationBell() {
  return (
    <button
      type="button"
      aria-label="Notifications"
      title="Notifications"
      className="flex h-9 w-9 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface-2 hover:text-ink"
    >
      <Bell className="h-5 w-5" />
    </button>
  );
}
