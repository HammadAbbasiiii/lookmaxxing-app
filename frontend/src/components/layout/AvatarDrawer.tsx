"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import {
  CreditCard,
  LayoutDashboard,
  LogOut,
  Settings as SettingsIcon,
  User as UserIcon,
  X,
} from "lucide-react";
import { useMe } from "@/hooks/useMe";
import { logout } from "@/lib/api/endpoints";
import { clearToken } from "@/lib/auth";
import { cn } from "@/lib/utils";

interface AvatarDrawerProps {
  open: boolean;
  onClose: () => void;
}

/** Mobile account drawer: slides in from the right with account + billing actions. */
export function AvatarDrawer({ open, onClose }: AvatarDrawerProps) {
  const router = useRouter();
  const { data: user } = useMe();
  const isAdmin = user?.is_admin === true;
  const isFree = (user?.subscription_tier ?? "free") === "free";

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  function go(href: string) {
    onClose();
    router.push(href);
  }

  async function handleSignOut() {
    onClose();
    await logout().catch(() => {});
    clearToken();
    router.replace("/");
  }

  return (
    <div
      className={cn(
        "fixed inset-0 z-50 overflow-hidden md:hidden",
        open ? "pointer-events-auto" : "pointer-events-none",
      )}
      aria-hidden={!open}
    >
      <div
        className={cn(
          "absolute inset-0 bg-black/50 transition-opacity duration-200",
          open ? "opacity-100" : "opacity-0",
        )}
        onClick={onClose}
      />
      <aside
        className={cn(
          "absolute right-0 top-0 flex h-full w-72 max-w-[85vw] flex-col border-l border-border-soft bg-background p-4 transition-transform duration-200",
          open ? "translate-x-0" : "translate-x-full",
        )}
        role="dialog"
        aria-modal="true"
        aria-label="Account menu"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate font-medium text-ink">{user?.full_name || "Member"}</p>
            <p className="truncate text-xs text-muted">{user?.email}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-2 text-muted transition-colors hover:text-ink"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="mt-4 flex flex-col gap-1">
          <DrawerItem icon={<UserIcon className="h-4 w-4" />} label="Profile" onClick={() => go("/settings")} />
          <DrawerItem icon={<SettingsIcon className="h-4 w-4" />} label="Settings" onClick={() => go("/settings")} />
          <DrawerItem
            icon={<CreditCard className="h-4 w-4" />}
            label={isFree ? "Upgrade" : "Subscription"}
            onClick={() => go(isFree ? "/upgrade" : "/settings")}
          />
          {isAdmin ? (
            <DrawerItem
              icon={<LayoutDashboard className="h-4 w-4" />}
              label="Admin Dashboard"
              onClick={() => go("/admin")}
            />
          ) : null}
        </nav>

        <div className="mt-auto border-t border-border-soft pt-2">
          <DrawerItem icon={<LogOut className="h-4 w-4" />} label="Log out" danger onClick={handleSignOut} />
        </div>
      </aside>
    </div>
  );
}

function DrawerItem({
  icon,
  label,
  onClick,
  danger = false,
}: {
  icon: ReactNode;
  label: string;
  onClick: () => void;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors",
        danger ? "text-danger hover:bg-surface-2" : "text-ink hover:bg-surface-2",
      )}
    >
      {icon}
      {label}
    </button>
  );
}
