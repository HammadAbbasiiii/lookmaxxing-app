"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CreditCard, Lock } from "lucide-react";
import { toast } from "sonner";
import { useMe } from "@/hooks/useMe";
import { cancelSubscription, deleteAccount, putProfile, resumeSubscription, type ProfileUpdate } from "@/lib/api/endpoints";
import { clearToken } from "@/lib/auth";
import { COMMITMENT_OPTIONS, GENDER_OPTIONS, GOAL_OPTIONS, PLANS, SKIN_CONCERN_OPTIONS, SKIN_TYPE_OPTIONS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/api/client";
import { normalizeTier, tierLabel } from "@/lib/tiers";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Skeleton } from "@/components/ui/Skeleton";
import { ScreenHeader } from "@/components/ui/ScreenHeader";

export default function SettingsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { data: user, isLoading } = useMe();

  const [fullName, setFullName] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("");
  const [goals, setGoals] = useState<string[]>([]);
  const [skinType, setSkinType] = useState("");
  const [skinConcerns, setSkinConcerns] = useState<string[]>([]);
  const [commitment, setCommitment] = useState("");
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [location, setLocation] = useState("");
  const [bio, setBio] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const [saving, setSaving] = useState(false);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);

  const [cancelOpen, setCancelOpen] = useState(false);
  const [billingBusy, setBillingBusy] = useState<null | "cancel" | "cancel-now" | "resume">(null);

  useEffect(() => {
    if (user && !hydrated) {
      setFullName(user.full_name ?? "");
      setAge(user.age?.toString() ?? "");
      setGender(user.gender ?? "");
      setGoals(user.goals ?? []);
      setSkinType(user.skin_type ?? "");
      setSkinConcerns(user.skin_concerns ?? []);
      setCommitment(user.commitment ?? "");
      setHeight(user.height?.toString() ?? "");
      setWeight(user.weight?.toString() ?? "");
      setLocation(user.location ?? "");
      setBio(user.bio ?? "");
      setHydrated(true);
    }
  }, [user, hydrated]);

  function toggleGoal(g: string) {
    setGoals((prev) => (prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g]));
  }

  function toggleSkinConcern(c: string) {
    setSkinConcerns((prev) => (prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]));
  }

  async function save() {
    const payload: ProfileUpdate = {};
    if (fullName.trim()) payload.full_name = fullName.trim();
    const ageNum = parseInt(age, 10);
    if (age && !Number.isNaN(ageNum)) payload.age = ageNum;
    if (gender) payload.gender = gender;
    if (goals.length) payload.goals = goals;
    if (skinType) payload.skin_type = skinType;
    if (skinConcerns.length) payload.skin_concerns = skinConcerns;
    if (commitment) payload.commitment = commitment;
    const heightNum = parseInt(height, 10);
    if (height && !Number.isNaN(heightNum)) payload.height = heightNum;
    const weightNum = parseInt(weight, 10);
    if (weight && !Number.isNaN(weightNum)) payload.weight = weightNum;
    if (location.trim()) payload.location = location.trim();
    if (bio.trim()) payload.bio = bio.trim();

    if (Object.keys(payload).length === 0) {
      toast.error("Change something first.");
      return;
    }

    setSaving(true);
    try {
      await putProfile(payload);
      toast.success("Profile updated.");
      qc.invalidateQueries({ queryKey: ["me"] });
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Couldn't save. Try again.");
    } finally {
      setSaving(false);
    }
  }

  async function doDelete() {
    setDeleting(true);
    try {
      await deleteAccount();
      clearToken();
      toast.success("Account deleted.");
      router.replace("/");
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Couldn't delete your account. Try again.");
      setDeleting(false);
    }
  }

  function fmtDate(iso: string | null | undefined): string {
    if (!iso) return "";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
  }

  async function doCancel(immediate: boolean) {
    setBillingBusy(immediate ? "cancel-now" : "cancel");
    try {
      await cancelSubscription(immediate);
      toast.success(
        immediate
          ? "Subscription cancelled — access removed."
          : "Cancellation scheduled for the end of your billing period.",
      );
      setCancelOpen(false);
      qc.invalidateQueries({ queryKey: ["me"] });
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Couldn't cancel your subscription. Try again.");
    } finally {
      setBillingBusy(null);
    }
  }

  async function doResume() {
    setBillingBusy("resume");
    try {
      await resumeSubscription();
      toast.success("Subscription resumed.");
      qc.invalidateQueries({ queryKey: ["me"] });
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Couldn't resume your subscription. Try again.");
    } finally {
      setBillingBusy(null);
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-40" />
        <Skeleton className="h-96 w-full rounded-card" />
      </div>
    );
  }

  const tier = user?.subscription_tier ?? "free";

  return (
    <div className="mx-auto max-w-xl">
      <ScreenHeader title="Settings" subtitle="Account control — profile, billing, and privacy." />

      {/* Profile */}
      <Card className="mb-4">
        <CardTitle>Profile</CardTitle>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Input id="full_name" label="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} maxLength={255} />
          <Input id="age" type="number" inputMode="numeric" label="Age" value={age} onChange={(e) => setAge(e.target.value)} min={13} max={99} />
          <Input id="height" type="number" inputMode="numeric" label="Height (cm)" value={height} onChange={(e) => setHeight(e.target.value)} />
          <Input id="weight" type="number" inputMode="numeric" label="Weight (kg)" value={weight} onChange={(e) => setWeight(e.target.value)} />
          <div className="sm:col-span-2">
            <Input id="location" label="Location" value={location} onChange={(e) => setLocation(e.target.value)} maxLength={255} />
          </div>
        </div>

        <div className="mt-4">
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
                  "rounded-xl border px-3 py-2 text-sm font-medium transition-colors",
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

        <div className="mt-4">
          <p className="mb-2 text-sm font-medium text-muted">Goals</p>
          <div className="flex flex-wrap gap-2">
            {GOAL_OPTIONS.map((opt) => {
              const active = goals.includes(opt.value);
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => toggleGoal(opt.value)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                    active
                      ? "border-gold bg-gold/15 text-gold-bright"
                      : "border-border-soft bg-surface-2 text-muted hover:text-ink",
                  )}
                >
                  {opt.emoji} {opt.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="mt-4">
          <p className="mb-2 text-sm font-medium text-muted">Skin type</p>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-5" role="radiogroup">
            {SKIN_TYPE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                role="radio"
                aria-checked={skinType === opt.value}
                onClick={() => setSkinType(opt.value)}
                className={cn(
                  "rounded-xl border px-2 py-2 text-sm font-medium transition-colors",
                  skinType === opt.value
                    ? "border-gold bg-gold/15 text-gold-bright"
                    : "border-border-soft bg-surface-2 text-muted hover:text-ink",
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-4">
          <p className="mb-2 text-sm font-medium text-muted">Skin concerns</p>
          <div className="flex flex-wrap gap-2">
            {SKIN_CONCERN_OPTIONS.map((opt) => {
              const active = skinConcerns.includes(opt.value);
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => toggleSkinConcern(opt.value)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                    active
                      ? "border-gold bg-gold/15 text-gold-bright"
                      : "border-border-soft bg-surface-2 text-muted hover:text-ink",
                  )}
                >
                  {opt.emoji} {opt.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="mt-4">
          <p className="mb-2 text-sm font-medium text-muted">Consistency</p>
          <div className="grid grid-cols-3 gap-2" role="radiogroup">
            {COMMITMENT_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                role="radio"
                aria-checked={commitment === opt.value}
                onClick={() => setCommitment(opt.value)}
                className={cn(
                  "rounded-xl border px-3 py-2 text-sm font-medium transition-colors",
                  commitment === opt.value
                    ? "border-gold bg-gold/15 text-gold-bright"
                    : "border-border-soft bg-surface-2 text-muted hover:text-ink",
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-4">
          <label htmlFor="bio" className="block text-sm font-medium text-muted">
            Bio
          </label>
          <textarea
            id="bio"
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            maxLength={500}
            rows={3}
            className="mt-1.5 w-full rounded-xl border border-border-soft bg-surface-2 px-3.5 py-2.5 text-sm text-ink placeholder:text-muted/60 focus:border-gold"
            placeholder="A little about you"
          />
        </div>

        <Button onClick={save} loading={saving} className="mt-5">
          Save changes
        </Button>
      </Card>

      {/* Subscription */}
      <Card className="mb-4">
        <CardTitle>Subscription</CardTitle>
        <div className="mt-3 flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-gold" aria-hidden />
              <p className="text-sm text-ink">
                Current plan:{" "}
                <Badge variant={tier === "free" ? "muted" : "gold"}>
                  {tierLabel(normalizeTier(tier))}
                </Badge>
              </p>
            </div>
            {tier === "free" ? (
              <Button variant="secondary" size="sm" onClick={() => router.push("/upgrade")}>
                Upgrade
              </Button>
            ) : null}
          </div>

          {tier !== "free" ? (
            <div className="rounded-xl border border-border-soft bg-surface-2 p-4">
              <p className="text-sm text-muted">
                {user?.subscription_cancels_at_period_end
                  ? `Cancels on ${fmtDate(user.subscription_end) || "the end of your billing period"}.`
                  : user?.subscription_end
                    ? `Renews on ${fmtDate(user.subscription_end)}.`
                    : "Active subscription."}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => router.push("/upgrade")}
                  disabled={billingBusy !== null}
                >
                  Change plan
                </Button>
                {user?.subscription_cancels_at_period_end ? (
                  <Button
                    size="sm"
                    onClick={doResume}
                    loading={billingBusy === "resume"}
                    disabled={billingBusy !== null}
                  >
                    Resume subscription
                  </Button>
                ) : (
                  <Button
                    variant="danger"
                    size="sm"
                    onClick={() => setCancelOpen(true)}
                    disabled={billingBusy !== null}
                  >
                    Cancel subscription
                  </Button>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </Card>

      {/* Cancel subscription confirm dialog */}
      {cancelOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Cancel subscription"
          onClick={() => billingBusy === null && setCancelOpen(false)}
        >
          <div className="w-full max-w-sm rounded-card card-border p-6" onClick={(e) => e.stopPropagation()}>
            <h2 className="font-display text-lg font-bold text-ink">
              Cancel {tierLabel(normalizeTier(tier))}?
            </h2>

            {/* Loss aversion (§5): surface exactly what they'll lose, not just
                what they'll stop paying — and keep "keep my plan" the primary. */}
            <div className="mt-3 rounded-xl border border-border-soft bg-surface-2 p-3">
              <p className="text-xs font-semibold uppercase tracking-widest text-muted">
                You&apos;ll lose access to
              </p>
              <ul className="mt-2 space-y-1.5">
                {(PLANS[tier === "elite" ? "elite" : "pro"].features as readonly string[]).map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-ink">
                    <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-gold" aria-hidden />
                    {f}
                  </li>
                ))}
              </ul>
            </div>

            <p className="mt-3 text-sm text-muted">
              Keep access until your renewal date, or cancel now and lose it immediately.
            </p>
            <div className="mt-4 flex flex-col gap-2">
              <Button
                onClick={() => setCancelOpen(false)}
                disabled={billingBusy !== null}
                fullWidth
              >
                Keep my plan
              </Button>
              <Button
                variant="secondary"
                onClick={() => doCancel(false)}
                disabled={billingBusy !== null}
                loading={billingBusy === "cancel"}
                fullWidth
              >
                Cancel at period end
              </Button>
              <Button
                variant="ghost"
                onClick={() => doCancel(true)}
                disabled={billingBusy !== null}
                loading={billingBusy === "cancel-now"}
                fullWidth
              >
                <span className="text-danger">Cancel now</span>
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Danger zone */}
      <Card className="border border-danger/20">
        <CardTitle className="text-danger">Danger zone</CardTitle>
        <p className="mt-2 text-sm text-muted">
          This permanently deletes your photos, plan, and progress. This can&apos;t be undone.
        </p>
        <Button variant="danger" className="mt-4" onClick={() => setConfirmOpen(true)}>
          <AlertTriangle className="h-4 w-4" /> Delete account
        </Button>
      </Card>

      {/* Delete confirm dialog */}
      {confirmOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          role="dialog"
          aria-modal="true"
          aria-label="Confirm account deletion"
          onClick={() => !deleting && setConfirmOpen(false)}
        >
          <div className="w-full max-w-sm rounded-card card-border p-6" onClick={(e) => e.stopPropagation()}>
            <h2 className="font-display text-lg font-bold text-ink">Delete your account?</h2>
            <p className="mt-2 text-sm text-muted">
              This permanently deletes your photos, plan, and progress. Type{" "}
              <strong className="text-danger">DELETE</strong> to confirm.
            </p>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="DELETE"
              className="mt-4 h-11 w-full rounded-xl border border-border-soft bg-surface-2 px-3.5 text-sm text-ink focus:border-danger"
              autoFocus
            />
            <div className="mt-4 flex gap-3">
              <Button variant="ghost" onClick={() => setConfirmOpen(false)} disabled={deleting}>
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={doDelete}
                disabled={confirmText !== "DELETE"}
                loading={deleting}
                fullWidth
              >
                Delete permanently
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
