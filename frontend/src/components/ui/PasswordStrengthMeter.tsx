"use client";

import { passwordStrength } from "@/lib/password";
import { cn } from "@/lib/utils";

const BAR_COLORS = [
  "bg-surface-2",   // 0 empty
  "bg-danger",      // 1 weak
  "bg-warning",     // 2 fair
  "bg-[#a3e635]",   // 3 good
  "bg-emerald-400", // 4 strong
];

const LABEL_COLORS = [
  "text-muted",
  "text-danger",
  "text-warning",
  "text-[#a3e635]",
  "text-emerald-400",
];

/** Live password strength meter with 4 bars + verdict copy (§7). */
export function PasswordStrengthMeter({ password }: { password: string }) {
  if (!password) return null;
  const s = passwordStrength(password);

  return (
    <div aria-live="polite" className="space-y-1.5">
      <div className="flex gap-1.5" aria-hidden>
        {[1, 2, 3, 4].map((i) => (
          <span
            key={i}
            className={cn(
              "h-1.5 flex-1 rounded-full transition-colors",
              i <= s.score ? BAR_COLORS[s.score] : "bg-surface-2",
            )}
          />
        ))}
      </div>
      <p className={cn("text-xs font-medium", LABEL_COLORS[s.score])}>
        {s.label}
        {s.label ? " — " : ""}
        <span className="text-muted">{s.hint}</span>
      </p>
    </div>
  );
}
