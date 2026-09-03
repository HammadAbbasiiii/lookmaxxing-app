"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CreditCard } from "lucide-react";
import { toast } from "sonner";
import { useMe } from "@/hooks/useMe";
import { deleteAccount, putProfile, type ProfileUpdate } from "@/lib/api/endpoints";
import { clearToken } from "@/lib/auth";
import { GENDER_OPTIONS, GOAL_OPTIONS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import { ApiError } from "@/lib/api/client";
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
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [location, setLocation] = useState("");
  const [bio, setBio] = useState("");
  const [hydrated, setHydrated] = useState(false);
  const [saving, setSaving] = useState(false);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (user && !hydrated) {
      setFullName(user.full_name ?? "");
      setAge(user.age?.toString() ?? "");
      setGender(user.gender ?? "");
      setGoals(user.goals ?? []);
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

  async function save() {
    const payload: ProfileUpdate = {};
    if (fullName.trim()) payload.full_name = fullName.trim();
    const ageNum = parseInt(age, 10);
    if (age && !Number.isNaN(ageNum)) payload.age = ageNum;
    if (gender) payload.gender = gender;
    if (goals.length) payload.goals = goals;
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
        <div className="mt-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CreditCard className="h-5 w-5 text-gold" aria-hidden />
            <p className="text-sm text-ink">
              Current plan:{" "}
              <Badge variant={tier === "free" ? "muted" : "gold"}>
                {tier === "free" ? "Free" : tier === "elite" ? "Elite" : "Pro"}
              </Badge>
            </p>
          </div>
          <Button variant="secondary" size="sm" onClick={() => router.push("/upgrade")}>
            {tier === "free" ? "Upgrade" : "Manage billing"}
          </Button>
        </div>
      </Card>

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
