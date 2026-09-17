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

/**
 * One calm sentence per server-confirmed stage, for screen readers only.
 * The visible copy above rotates for flavour; announcing that rotation every
 * 2.5s would make a screen reader unusable, so the *live region* below only
 * ever speaks when the pipeline genuinely moves.
 */
const STAGE_ANNOUNCEMENT: Record<string, string> = {
  pending: "Your photo is queued for analysis.",
  processing: "Analysis in progress.",
  completed: "Analysis complete.",
};

/**
 * How long we stay silent before acknowledging that this is taking a while.
 * The anxiety peak of this screen is not the first seconds — it's the moment
 * silence starts to feel like failure (~20s), so that is exactly when we speak
 * up with the one thing the user actually wants to know: nothing is lost.
 */
const SLOW_ANALYSIS_SEC = 20;

/**
 * Pipeline stages the server actually reports. We map them to ring positions so
 * the UI only ever advances on a real state change — the previous implementation
 * interpolated from wall-clock time and hard-capped at 95%, which was simply a
 * fabricated progress bar. The elapsed timer below is the honest signal.
 */
const STAGE_PROGRESS: Record<string, number> = {
  pending: 25,
  processing: 65,
  completed: 100,
};

export default function AnalyzingPage() {
  const params = useParams<{ photo_id: string }>();
  const router = useRouter();
  const photoId = Array.isArray(params.photo_id) ? params.photo_id[0] : params.photo_id;

  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState<string | null>(null);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [copyIndex, setCopyIndex] = useState(0);
  const [failed, setFailed] = useState(false);
  const [timedOut, setTimedOut] = useState(false);
  const [pollKey, setPollKey] = useState(0);

  // Rotating reassurance copy (§8.6).
  useEffect(() => {
    const id = setInterval(() => setCopyIndex((i) => (i + 1) % COPY.length), 2500);
    return () => clearInterval(id);
  }, []);

  // Honest timer: the only thing we can truthfully show while we don't know how
  // far along the server is.
  useEffect(() => {
    const id = setInterval(() => setElapsedSec((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [pollKey]);

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
      try {
        const s = await getPhotoStatus(photoId);
        if (cancelled) return;
        // Advance the ring only on a stage the server actually confirms.
        setProgress(STAGE_PROGRESS[s.analysis_status] ?? 20);
        setStage(s.analysis_status);
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
          <span className="tabular text-sm font-semibold text-ink">{elapsedSec}s</span>
        </ProgressRing>
      </div>

      {/* Screen-reader status: one calm sentence per *real* stage change. The
          visible copy rotates every 2.5s for flavour — announcing that would
          make the page unusable with a screen reader, so the rotation below is
          deliberately not a live region. */}
      <p className="sr-only" role="status" aria-live="polite">
        {stage ? (STAGE_ANNOUNCEMENT[stage] ?? "") : ""}
      </p>

      {/* `key` remounts this line, so each rotation crossfades in (260ms) rather
          than hard-swapping — the difference between "it's thinking" and "it
          changed its mind". */}
      <p
        key={copyIndex}
        className="swap-in mt-6 text-center font-display text-lg font-semibold text-ink"
      >
        {COPY[copyIndex]}
      </p>
      <p className="mt-1 text-center text-sm text-muted">
        Usually under a minute. You can leave — your result will be waiting.
      </p>

      {/* The anxiety peak of this screen isn't second one — it's the moment the
          silence starts to feel like failure. Speak up exactly then, and answer
          the only question the user actually has: is my photo lost? */}
      {elapsedSec >= SLOW_ANALYSIS_SEC ? (
        <p className="swap-in mt-4 max-w-xs text-center text-xs leading-relaxed text-muted">
          Taking longer than usual — nothing is lost. Your photo stays private,
          and your result will be waiting on your dashboard.
        </p>
      ) : null}

      <Button variant="ghost" className="mt-8" onClick={() => router.push("/dashboard")}>
        Cancel
      </Button>
    </div>
  );
}
