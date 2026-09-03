"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import imageCompression from "browser-image-compression";
import { Camera, ImagePlus, ShieldCheck, X } from "lucide-react";
import { toast } from "sonner";
import { ScreenHeader } from "@/components/ui/ScreenHeader";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Skeleton";
import { ApiError } from "@/lib/api/client";
import { analyzePhoto, getUploadSignature, saveDirectUpload } from "@/lib/api/endpoints";
import { uploadDirectToCloudinary } from "@/lib/api/cloudinary";
import { useEntitlements } from "@/hooks/useEntitlements";
import { PaywallLock } from "@/components/ui/PaywallLock";
import { ACCEPTED_IMAGE_TYPES, MAX_DIMENSION_PX, MAX_FILE_SIZE_MB } from "@/lib/constants";
import { cn } from "@/lib/utils";

type Stage = "idle" | "compressing" | "uploading" | "saving" | "starting";

const STAGE_LABEL: Record<Stage, string> = {
  idle: "",
  compressing: "Compressing…",
  uploading: "Uploading…",
  saving: "Saving…",
  starting: "Starting analysis…",
};

export default function UploadPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);

  const ent = useEntitlements();
  const hitLimit = Boolean(
    ent.data &&
      !ent.data.limits.analyses.unlimited &&
      (ent.data.limits.analyses.remaining ?? 1) === 0,
  );

  function reset() {
    setFile(null);
    setPreview(null);
    setError(null);
    setStage("idle");
  }

  function onSelectFile(f: File | null) {
    setError(null);
    if (!f) return;

    if (!ACCEPTED_IMAGE_TYPES.includes(f.type as (typeof ACCEPTED_IMAGE_TYPES)[number])) {
      setError("Use a JPG, PNG, or HEIC file.");
      return;
    }
    if (f.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setError("That photo is too big. Max 10MB.");
      return;
    }

    setFile(f);
    if (preview) URL.revokeObjectURL(preview);
    setPreview(URL.createObjectURL(f));
  }

  function mapUploadError(e: unknown): string {
    if (e instanceof ApiError) {
      if (e.status === 429) return "Too many requests. Wait a moment.";
      if (e.status === 413) return "That photo is too big. Max 10MB.";
      if (e.code === "timeout") return "Upload is taking too long. Try a smaller photo.";
      if (e.code === "network") return "No connection. Check your signal.";
      return e.message;
    }
    if (e instanceof Error) {
      if (/too long|smaller photo|No connection|upload failed/i.test(e.message)) return e.message;
    }
    return "Something went wrong. Please try again.";
  }

  async function handleUpload() {
    if (!file) return;
    setError(null);

    try {
      setStage("compressing");
      const compressed = await imageCompression(file, {
        maxSizeMB: 1,
        maxWidthOrHeight: MAX_DIMENSION_PX,
        useWebWorker: true,
        initialQuality: 0.75,
        fileType: "image/jpeg",
      });

      setStage("uploading");
      const signature = await getUploadSignature();
      const secureUrl = await uploadDirectToCloudinary(signature, compressed);

      setStage("saving");
      const saved = await saveDirectUpload(secureUrl, signature.public_id);

      setStage("starting");
      try {
        await analyzePhoto(saved.photo_id);
      } catch (e) {
        if (e instanceof ApiError && e.status === 403) {
          toast.error("Upgrade to Pro to unlock more analyses.");
          router.push("/upgrade");
          return;
        }
        throw e;
      }

      router.push(`/analyzing/${saved.photo_id}`);
    } catch (e) {
      setError(mapUploadError(e));
      setStage("idle");
    }
  }

  if (hitLimit) {
    return (
      <div className="mx-auto max-w-md">
        <ScreenHeader title="Get your score" subtitle="You've used your free analysis." />
        <PaywallLock
          title="Unlimited analyses"
          teaser="Re-score every week and watch your face change in the before/after."
          description="Free tier includes 1 analysis. Pro unlocks unlimited uploads, the full report, and your daily coach."
        />
      </div>
    );
  }

  const busy = stage !== "idle";

  return (
    <div className="mx-auto max-w-md">
      <ScreenHeader
        title="Get your score"
        subtitle="Face the light. Look straight. We'll handle the rest."
      />

      <div className="card-border rounded-card p-6">
        <div
          className={cn(
            "relative flex aspect-square w-full flex-col items-center justify-center overflow-hidden rounded-xl border border-dashed border-border-soft bg-surface-2",
            !preview && !busy && "cursor-pointer",
          )}
          onClick={() => !preview && !busy && fileRef.current?.click()}
        >
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="Selected" className="h-full w-full object-cover" />
          ) : (
            <div className="flex flex-col items-center px-6 text-center">
              <ImagePlus className="mb-3 h-8 w-8 text-gold" aria-hidden />
              <p className="text-sm font-medium text-ink">Choose a photo</p>
              <p className="mt-1 text-xs text-muted">A clear front-facing selfie works best</p>
            </div>
          )}

          {busy ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-background/80">
              <Spinner className="h-8 w-8" />
              <p className="mt-3 text-sm text-ink">{STAGE_LABEL[stage]}</p>
            </div>
          ) : null}

          {preview && !busy ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                reset();
              }}
              className="absolute right-2 top-2 rounded-full bg-black/70 p-1.5 text-ink"
              aria-label="Remove photo"
            >
              <X className="h-4 w-4" />
            </button>
          ) : null}
        </div>

        {error ? (
          <p className="mt-3 rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger" role="alert">
            {error}
          </p>
        ) : null}

        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/heic"
          className="hidden"
          onChange={(e) => onSelectFile(e.target.files?.[0] ?? null)}
        />
        <input
          ref={cameraRef}
          type="file"
          accept="image/jpeg,image/png,image/heic"
          capture="user"
          className="hidden"
          onChange={(e) => onSelectFile(e.target.files?.[0] ?? null)}
        />

        <div className="mt-5 flex gap-3">
          <Button variant="secondary" onClick={() => cameraRef.current?.click()} disabled={busy} fullWidth>
            <Camera className="h-4 w-4" /> Take photo
          </Button>
          <Button
            onClick={() => (file ? handleUpload() : fileRef.current?.click())}
            disabled={busy}
            loading={busy}
            fullWidth
          >
            {file ? (busy ? "Working…" : "Analyze photo") : "Choose photo"}
          </Button>
        </div>

        <p className="mt-4 flex items-center justify-center gap-1.5 text-center text-xs text-muted">
          <ShieldCheck className="h-3.5 w-3.5 text-gold" aria-hidden />
          Your photo is private and deleted anytime. Max 10MB.
        </p>
      </div>
    </div>
  );
}
