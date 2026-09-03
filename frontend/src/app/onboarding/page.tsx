"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Logo } from "@/components/layout/Logo";
import { Spinner } from "@/components/ui/Skeleton";
import { COMMITMENT_OPTIONS, GENDER_OPTIONS, GOAL_OPTIONS } from "@/lib/constants";
import { completeOnboarding, putProfile } from "@/lib/api/endpoints";
import { cn } from "@/lib/utils";

const STEPS = ["Tell us about you", "Pick one goal", "Consistency beats intensity"];

export default function OnboardingPage() {
  const ready = useRequireAuth();
  const router = useRouter();

  const [step, setStep] = useState(0);
  const [age, setAge] = useState("");
  const [ageError, setAgeError] = useState("");
  const [gender, setGender] = useState("");
  const [goal, setGoal] = useState("");
  const [commitment, setCommitment] = useState("");
  const [saving, setSaving] = useState(false);

  function canNext(): boolean {
    if (step === 0) {
      const ageNum = parseInt(age, 10);
      return !Number.isNaN(ageNum) && ageNum >= 13 && ageNum <= 99 && Boolean(gender);
    }
    if (step === 1) return Boolean(goal);
    if (step === 2) return Boolean(commitment);
    return true;
  }

  function next() {
    if (step === 0) {
      const ageNum = parseInt(age, 10);
      if (Number.isNaN(ageNum)) {
        setAgeError("Enter your age.");
        return;
      }
      if (ageNum < 13) {
        setAgeError("LookMaxx is for 13+.");
        return;
      }
      if (ageNum > 99) {
        setAgeError("Enter a valid age.");
        return;
      }
      setAgeError("");
    }
    if (step < 2) setStep((s) => s + 1);
    else finish();
  }

  function skip() {
    if (step < 2) setStep((s) => s + 1);
    else finish();
  }

  async function finish() {
    setSaving(true);
    const ageNum = parseInt(age, 10);
    const goals = goal ? [goal] : undefined;
    try {
      await putProfile({
        age: Number.isNaN(ageNum) ? undefined : ageNum,
        gender: gender || undefined,
        goals,
      });
    } catch {
      toast.error("Couldn't save your details — you can update them later in Settings.");
    }
    try {
      await completeOnboarding();
    } catch {
      /* onboarding can be completed later */
    }
    toast.success("You're locked in. Let's get your score.");
    router.replace("/upload");
  }

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Spinner className="h-6 w-6" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12">
      <div className="mb-8">
        <Logo />
      </div>

      <div className="mb-8 flex items-center gap-2" aria-label={`Step ${step + 1} of 3`}>
        {STEPS.map((_, i) => (
          <span
            key={i}
            className={cn(
              "h-2 rounded-full transition-all",
              i === step ? "w-8 gold-gradient" : i < step ? "w-2 bg-gold" : "w-2 bg-surface-2",
            )}
          />
        ))}
      </div>

      <div className="w-full max-w-sm card-border rounded-card p-7">
        <p className="mb-1 text-xs uppercase tracking-wide text-muted">
          Step {step + 1} of 3
        </p>
        <h1 className="font-display text-xl font-bold text-ink">{STEPS[step]}</h1>
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          className="mt-5"
        >
          {step === 0 ? (
            <div className="space-y-5">
              <Input
                id="age"
                type="number"
                inputMode="numeric"
                label="Your age"
                placeholder="e.g. 24"
                value={age}
                onChange={(e) => {
                  setAge(e.target.value);
                  setAgeError("");
                }}
                error={ageError}
                min={13}
                max={99}
              />
              <div>
                <p className="mb-2 text-sm font-medium text-muted">Gender</p>
                <div className="grid grid-cols-3 gap-2" role="radiogroup">
                  {GENDER_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      role="radio"
                      aria-checked={gender === opt.value}
                      onClick={() => setGender(opt.value)}
                      className={cn(
                        "rounded-xl border px-3 py-2.5 text-sm font-medium transition-colors",
                        gender === opt.value
                          ? "border-gold bg-gold/15 text-gold-bright"
                          : "border-border-soft bg-surface-2 text-muted hover:text-ink",
                      )}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
          {step === 1 ? (
            <div className="space-y-2" role="radiogroup">
              {GOAL_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  role="radio"
                  aria-checked={goal === opt.value}
                  onClick={() => setGoal(opt.value)}
                  className={cn(
                    "flex w-full items-center justify-between rounded-xl border px-4 py-3 text-sm font-medium transition-all",
                    goal === opt.value
                      ? "border-gold bg-gold/15 text-ink"
                      : "border-border-soft bg-surface-2 text-muted hover:text-ink",
                  )}
                >
                  <span>
                    <span className="mr-2">{opt.emoji}</span>
                    {opt.label}
                  </span>
                  {goal === opt.value ? <span className="text-gold">✓</span> : null}
                </button>
              ))}
            </div>
          ) : null}
          {step === 2 ? (
            <div className="space-y-2" role="radiogroup">
              {COMMITMENT_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  role="radio"
                  aria-checked={commitment === opt.value}
                  onClick={() => setCommitment(opt.value)}
                  className={cn(
                    "w-full rounded-xl border px-4 py-3 text-sm font-medium transition-all",
                    commitment === opt.value
                      ? "border-gold bg-gold/15 text-ink"
                      : "border-border-soft bg-surface-2 text-muted hover:text-ink",
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          ) : null}
        </motion.div>

        <div className="mt-6 flex items-center gap-3">
          {step > 0 ? (
            <Button variant="ghost" onClick={() => setStep((s) => s - 1)}>
              Back
            </Button>
          ) : null}
          <Button variant="ghost" onClick={skip} className="ml-auto">
            Skip
          </Button>
          <Button onClick={next} disabled={!canNext()} loading={saving} className="min-w-[96px]">
            {step === 2 ? "Finish" : "Next"}
          </Button>
        </div>
      </div>
    </div>
  );
}
