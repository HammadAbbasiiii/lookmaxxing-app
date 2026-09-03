"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Logo } from "@/components/layout/Logo";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api/client";
import { login } from "@/lib/api/endpoints";
import { setToken } from "@/lib/auth";
import { safeNext } from "@/lib/utils";

const loginSchema = z.object({
  email: z
    .string()
    .trim()
    .toLowerCase()
    .min(1, "Email is required.")
    .max(254, "Email is too long.")
    .refine((v) => /^[^\s@]+@[^\s@]+$/.test(v), "Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

type LoginInput = z.infer<typeof loginSchema>;

export function LoginForm({
  next,
  initialEmail,
}: {
  next: string;
  initialEmail: string;
}) {
  const router = useRouter();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    mode: "onBlur",
    defaultValues: { email: initialEmail, password: "" },
  });

  async function onSubmit(values: LoginInput) {
    try {
      const token = await login(values.email, values.password);
      setToken(token.access_token);
      toast.success("Welcome back.");
      router.replace(safeNext(next));
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        // Anti-enumeration: identical copy for wrong email and wrong password.
        setError("root", { message: "Incorrect email or password." });
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
      <h1 className="text-center font-display text-2xl font-bold text-ink">Welcome back</h1>
      <p className="mt-1 text-center text-sm text-muted">Your score is waiting.</p>

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
          enterKeyHint="go"
          label="Email"
          placeholder="you@example.com"
          maxLength={254}
          error={errors.email?.message}
          {...register("email")}
        />
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          enterKeyHint="go"
          label="Password"
          placeholder="Your password"
          error={errors.password?.message}
          {...register("password")}
        />

        <Button type="submit" fullWidth loading={isSubmitting}>
          {isSubmitting ? "Logging in…" : "Log in"}
        </Button>
      </form>

      <p className="mt-5 text-center text-sm text-muted">
        No account?{" "}
        <Link href="/signup" className="font-medium text-gold hover:text-gold-bright">
          Create account
        </Link>
      </p>
    </div>
  );
}
