"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ScanLine } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { ProgressRing } from "@/components/ui/ProgressRing";
import { ErrorCard } from "@/components/ui/ErrorCard";
import { getPhotoStatus } from "@/lib/api/endpoints";
import { POLL_INTERVAL_MS, POLL_MAX_MS } from "@/lib/constants";

const COPY = [
  "Reading your features…",
  "Measuring symmetry…",
  "Analyzing skin & jawline…",
  "Building your 90-day plan…",
  "Almost there…",
];

export default function AnalyzingPage() {
  const params = useParams<{ photo_id: string }>();
  const router = useRouter();
  const photoId = Array.isArray(params.photo_id) ? params.photo_id[0] : params.photo_id;

  const [progress, setProgress] = useState(0);
  const [copyIndex, setCopyIndex] = useState(0);
  const [failed, setFailed] = useState(false);
  const [timedOut, setTimedOut] = useState(false);
  const [pollKey, setPollKey] = useState(0);

  // Rotating reassurance copy (§8.6).
  useEffect(() => {
    const id = setInterval(() => setCopyIndex((i) => (i + 1) % COPY.length), 2500);
    return () => clearInterval(id);
  }, []);

  // Poll analysis status (§4.4) — guarded so we never setState after unmount.
  useEffect(() => {
    let cancelled = false;
    let interval: ReturnType<typeof setInterval> | undefined;
    const startedAt = Date.now();

    async function poll() {
      if (cancelled) return;
      const elapsed = Date.now() - startedAt;
      if (elapsed > POLL_MAX_MS) {
        setTimedOut(true);
        if (interval) clearInterval(interval);
        return;
      }
      setProgress(Math.min(95, Math.round((elapsed / POLL_MAX_MS) * 100)));

      try {
        const s = await getPhotoStatus(photoId);
        if (cancelled) return;
        if (s.analysis_status === "completed" || s.score != null) {
          router.replace(`/results/${photoId}`);
          return;
        }
        if (s.analysis_status === "failed") {
          setFailed(true);
          if (interval) clearInterval(interval);
          return;
        }
      } catch {
        // Network hiccup — keep last state; the OfflineBanner communicates it.
      }
    }

    poll();
    interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      if (interval) clearInterval(interval);
    };
  }, [photoId, router, pollKey]);

  if (failed) {
    return (
      <div className="mx-auto max-w-md pt-10">
        <ErrorCard
          title="Analysis couldn't complete"
          message="Analysis couldn't complete. Try a clearer photo."
          onRetry={() => router.push("/upload")}
          actionLabel="Upload again"
        />
      </div>
    );
  }

  if (timedOut) {
    return (
      <div className="mx-auto max-w-md pt-10">
        <ErrorCard
          title="Still working…"
          message="Still working… give it a moment, or retry."
          onRetry={() => {
            setTimedOut(false);
            setProgress(0);
            setPollKey((k) => k + 1);
          }}
          actionLabel="Retry"
        />
        <div className="mt-4 text-center">
          <Button variant="ghost" onClick={() => router.push("/dashboard")}>
            Back to dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-md flex-col items-center pt-10">
      <div className="relative flex aspect-square w-full items-center justify-center overflow-hidden rounded-card card-border">
        <div className="flex h-full w-full items-center justify-center bg-surface-2 text-muted">
          <ScanLine className="h-10 w-10" aria-hidden />
        </div>
        {/* Scan sweep overlay */}
        <div className="pointer-events-none absolute inset-x-0 top-0 h-1/3 bg-gradient-to-b from-gold/20 to-transparent" />
      </div>

      <div className="mt-8">
        <ProgressRing value={progress} size={96} stroke={8}>
          <span className="tabular text-sm font-semibold text-ink">{progress}%</span>
        </ProgressRing>
      </div>

      <p className="mt-6 text-center font-display text-lg font-semibold text-ink">
        {COPY[copyIndex]}
      </p>
      <p className="mt-1 text-center text-sm text-muted">
        This usually takes under 30 seconds. You can leave — your result will be waiting.
      </p>

      <Button variant="ghost" className="mt-8" onClick={() => router.push("/dashboard")}>
        Cancel
      </Button>
    </div>
  );
}
