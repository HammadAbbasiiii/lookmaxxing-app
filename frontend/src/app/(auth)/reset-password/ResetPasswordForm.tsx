"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { resetPassword, verifyResetToken } from "@/lib/api/endpoints";
import { passwordSchema } from "@/lib/password";
import { PasswordStrengthMeter } from "@/components/ui/PasswordStrengthMeter";

const resetSchema = z
  .object({
    new_password: passwordSchema,
    confirm: z.string(),
  })
  .refine((d) => d.new_password === d.confirm, {
    message: "Passwords don't match.",
    path: ["confirm"],
  });

type ResetInput = z.infer<typeof resetSchema>;

export function ResetPasswordForm({ token }: { token: string }) {
  const router = useRouter();
  const [state, setState] = useState<"checking" | "ready" | "invalid">("checking");

  const {
    register,
    handleSubmit,
    setError,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ResetInput>({
    resolver: zodResolver(resetSchema),
    mode: "onBlur",
    defaultValues: { new_password: "", confirm: "" },
  });
  const passwordValue = watch("new_password") ?? "";

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await verifyResetToken(token);
        if (!cancelled) setState("ready");
      } catch {
        if (!cancelled) setState("invalid");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function onSubmit(values: ResetInput) {
    try {
      await resetPassword(token, values.new_password);
      toast.success("Password updated. Log in with your new password.");
      router.replace("/login");
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) {
        setState("invalid");
      } else if (error instanceof ApiError && error.status === 429) {
        setError("root", { message: "Too many attempts. Wait a minute and try again." });
      } else {
        const message = error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
        setError("root", { message });
      }
    }
  }

  if (state === "checking") {
    return (
      <div className="card-border rounded-card p-7">
        <div className="mb-6 flex justify-center">
          <Logo />
        </div>
        <p className="text-center text-sm text-muted">Checking your reset link…</p>
      </div>
    );
  }

  if (state === "invalid") {
    return (
      <div className="card-border rounded-card p-7">
        <div className="mb-6 flex justify-center">
          <Logo />
        </div>
        <h1 className="text-center font-display text-2xl font-bold text-ink">Link expired</h1>
        <p className="mt-2 text-center text-sm text-muted">
          This reset link is invalid or has expired. Request a new one to continue.
        </p>
        <Link href="/forgot-password" className="mt-6 block w-full">
          <Button type="button" fullWidth>
            Request a new link
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="card-border rounded-card p-7">
      <div className="mb-6 flex justify-center">
        <Logo />
      </div>
      <h1 className="text-center font-display text-2xl font-bold text-ink">Set a new password</h1>
      <p className="mt-1 text-center text-sm text-muted">Choose a strong password you haven&apos;t used before.</p>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4" noValidate>
        {errors.root ? (
          <p className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger" role="alert">
            {errors.root.message}
          </p>
        ) : null}

        <Input
          id="new_password"
          type="password"
          autoComplete="new-password"
          enterKeyHint="next"
          label="New password"
          placeholder="At least 8 characters"
          error={errors.new_password?.message}
          {...register("new_password")}
        />
        <PasswordStrengthMeter password={passwordValue} />
        <Input
          id="confirm"
          type="password"
          autoComplete="new-password"
          enterKeyHint="go"
          label="Confirm new password"
          placeholder="Repeat your password"
          error={errors.confirm?.message}
          {...register("confirm")}
        />

        <Button type="submit" fullWidth loading={isSubmitting}>
          {isSubmitting ? "Updating…" : "Update password"}
        </Button>
      </form>
    </div>
  );
}
