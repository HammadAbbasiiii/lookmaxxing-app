"use client";

import { forwardRef, useState } from "react";
import type { InputHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";
import { cn } from "@/lib/utils";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  id: string;
}

/** Text/password input with label, error, and a password visibility toggle. */
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, id, type = "text", className, ...props },
  ref,
) {
  const [show, setShow] = useState(false);
  const isPassword = type === "password";
  const resolvedType = isPassword ? (show ? "text" : "password") : type;

  return (
    <div className="space-y-1.5">
      {label ? (
        <label htmlFor={id} className="block text-sm font-medium text-muted">
          {label}
        </label>
      ) : null}
      <div className="relative">
        <input
          ref={ref}
          id={id}
          type={resolvedType}
          className={cn(
            "h-11 w-full rounded-xl border border-border-soft bg-surface-2 px-3.5 text-sm text-ink placeholder:text-muted/60 transition-colors focus:border-gold",
            error && "border-danger/60",
            isPassword && "pr-11",
            className,
          )}
          aria-invalid={Boolean(error)}
          {...props}
        />
        {isPassword ? (
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted transition-colors hover:text-ink"
            aria-label={show ? "Hide password" : "Show password"}
          >
            {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        ) : null}
      </div>
      {error ? (
        <p className="text-xs text-danger" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
});
