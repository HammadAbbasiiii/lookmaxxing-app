"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, Inbox } from "lucide-react";

/**
 * Notification bell (top-right, next to avatar).
 *
 * There is no backend notifications feature yet, so this shows an honest
 * "no notifications" dropdown instead of a dead button. Wire it to a
 * `/notifications` endpoint + unread badge once notifications land.
 */
export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label="Notifications"
        aria-expanded={open}
        title="Notifications"
        onClick={() => setOpen((v) => !v)}
        className="flex h-9 w-9 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface-2 hover:text-ink"
      >
        <Bell className="h-5 w-5" />
      </button>

      <AnimatePresence>
        {open ? (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 z-50 mt-2 w-72 rounded-card card-border bg-surface p-4 shadow-xl"
            role="dialog"
            aria-label="Notifications"
          >
            <p className="flex items-center gap-2 text-sm font-semibold text-ink">
              <Inbox className="h-4 w-4 text-muted" /> No notifications
            </p>
            <p className="mt-1 text-xs text-muted">
              You&apos;re all caught up. Milestones and rewards will show up here.
            </p>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}

