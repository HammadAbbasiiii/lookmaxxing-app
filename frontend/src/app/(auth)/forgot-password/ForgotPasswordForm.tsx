"use client";

import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { requestPasswordReset } from "@/lib/api/endpoints";

const forgotSchema = z.object({
  email: z
    .string()
    .trim()
    .toLowerCase()
    .min(1, "Email is required.")
    .max(254, "Email is too long.")
    .refine((v) => /^[^\s@]+@[^\s@]+$/.test(v), "Enter a valid email address."),
});

type ForgotInput = z.infer<typeof forgotSchema>;

export function ForgotPasswordForm() {
  const [sent, setSent] = useState(false);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ForgotInput>({
    resolver: zodResolver(forgotSchema),
    mode: "onBlur",
    defaultValues: { email: "" },
  });

  async function onSubmit(values: ForgotInput) {
    try {
      await requestPasswordReset(values.email);
      // Always show success (anti-enumeration mirrors the backend) regardless of
      // whether the address actually exists.
      setSent(true);
    } catch (error) {
      if (error instanceof ApiError && error.status === 429) {
        setError("root", { message: "Too many requests. Wait a few minutes and try again." });
      } else {
        const message = error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
        setError("root", { message });
      }
    }
  }

  if (sent) {
    return (
      <div className="card-border rounded-card p-7">
        <div className="mb-6 flex justify-center">
          <Logo />
        </div>
        <h1 className="text-center font-display text-2xl font-bold text-ink">Check your inbox</h1>
        <p className="mt-2 text-center text-sm text-muted">
          If an account exists for that email, a reset link is on its way. The link expires in 30
          minutes.
        </p>
        <Link href="/login" className="mt-6 block w-full">
          <Button type="button" fullWidth variant="secondary">
            Back to log in
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
      <h1 className="text-center font-display text-2xl font-bold text-ink">Forgot your password?</h1>
      <p className="mt-1 text-center text-sm text-muted">
        Enter your email and we&apos;ll send a reset link.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4" noValidate>
        {errors.root ? (
          <p className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger" role="alert">
            {errors.root.message}
          </p>
        ) : null}

        <Input
          id="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          enterKeyHint="send"
          label="Email"
          placeholder="you@example.com"
          maxLength={254}
          error={errors.email?.message}
          {...register("email")}
        />

        <Button type="submit" fullWidth loading={isSubmitting}>
          {isSubmitting ? "Sending…" : "Send reset link"}
        </Button>
      </form>

      <p className="mt-5 text-center text-sm text-muted">
        Remembered it?{" "}
        <Link href="/login" className="font-medium text-gold hover:text-gold-bright">
          Log in
        </Link>
      </p>
    </div>
  );
}
