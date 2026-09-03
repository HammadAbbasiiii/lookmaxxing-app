"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { login, signup } from "@/lib/api/endpoints";
import { setToken } from "@/lib/auth";

// Email check is intentionally lenient so it never over-rejects international
// (Unicode) addresses (§9.2 #17); the backend EmailStr is the real validator.
const signupSchema = z.object({
  email: z
    .string()
    .trim()
    .toLowerCase()
    .min(1, "Email is required.")
    .max(254, "Email is too long.")
    .refine((v) => /^[^\s@]+@[^\s@]+$/.test(v), "Enter a valid email address."),
  password: z
    .string()
    .trim()
    .min(1, "Password is required.")
    .min(6, "Password must be at least 6 characters."),
  full_name: z.string().trim().max(255, "Name is too long.").optional(),
  consent: z.boolean().refine((v) => v === true, "Please agree to continue."),
});

type SignupInput = z.infer<typeof signupSchema>;

export function SignupForm() {
  const router = useRouter();
  const [duplicate, setDuplicate] = useState(false);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<SignupInput>({
    resolver: zodResolver(signupSchema),
    mode: "onBlur",
    defaultValues: { email: "", password: "", full_name: "", consent: false },
  });

  async function onSubmit(values: SignupInput) {
    setDuplicate(false);
    try {
      await signup(values.email, values.password, values.full_name);
      toast.success("Account created.");
      try {
        const token = await login(values.email, values.password);
        setToken(token.access_token);
        router.replace("/onboarding");
      } catch {
        router.replace(`/login?email=${encodeURIComponent(values.email)}`);
        toast.info("Account created — log in to continue.");
      }
    } catch (error) {
      if (error instanceof ApiError && error.status === 400 && /registered/i.test(error.message)) {
        setDuplicate(true);
        setError("email", { message: "That email is already registered. Log in instead." });
      } else if (error instanceof ApiError && error.status === 429) {
        setError("root", { message: "Too many attempts. Wait a minute and try again." });
        toast.error("Too many attempts. Wait a minute and try again.");
      } else {
        const message = error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
        setError("root", { message });
        toast.error(message);
      }
    }
  }

  return (
    <div className="card-border rounded-card p-7">
      <div className="mb-6 flex justify-center">
        <Logo />
      </div>
      <h1 className="text-center font-display text-2xl font-bold text-ink">Create your account</h1>
      <p className="mt-1 text-center text-sm text-muted">Your score is private. Takes 60 seconds.</p>

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
          label="Email"
          placeholder="you@example.com"
          maxLength={254}
          error={errors.email?.message}
          {...register("email")}
        />
        <Input
          id="full_name"
          type="text"
          autoComplete="name"
          label="First name (optional)"
          placeholder="Alex"
          maxLength={255}
          error={errors.full_name?.message}
          {...register("full_name")}
        />
        <Input
          id="password"
          type="password"
          autoComplete="new-password"
          label="Password"
          placeholder="At least 6 characters"
          error={errors.password?.message}
          {...register("password")}
        />

        <label className="flex items-start gap-2.5 text-xs text-muted">
          <input
            type="checkbox"
            className="mt-0.5 h-4 w-4 shrink-0 accent-[#d4af37]"
            aria-invalid={Boolean(errors.consent)}
            {...register("consent")}
          />
          <span>
            I agree to the{" "}
            <Link href="/terms" className="text-gold hover:text-gold-bright">
              Terms
            </Link>{" "}
            and{" "}
            <Link href="/privacy" className="text-gold hover:text-gold-bright">
              Privacy Policy
            </Link>
            , and I consent to my photo being used to generate my score.
          </span>
        </label>
        {errors.consent ? (
          <p className="text-xs text-danger" role="alert">
            {errors.consent.message}
          </p>
        ) : null}

        <Button type="submit" fullWidth loading={isSubmitting}>
          {isSubmitting ? "Creating…" : "Create account"}
        </Button>
      </form>

      <p className="mt-5 text-center text-sm text-muted">
        Already have an account?{" "}
        {duplicate ? (
          <Link href="/login" className="font-medium text-gold hover:text-gold-bright">
            Log in instead
          </Link>
        ) : (
          <Link href="/login" className="font-medium text-gold hover:text-gold-bright">
            Log in
          </Link>
        )}
      </p>
    </div>
  );
}
