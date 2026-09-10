"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { RefreshCw, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Skeleton";
import { cn } from "@/lib/utils";
import {
  computeBlurScore,
  computeBrightness,
  evaluateFrame,
  loadFaceDetector,
  type FaceBox,
  type Guidance,
} from "@/lib/camera";

type CamStatus = "starting" | "active" | "error" | "denied" | "unavailable";

interface CameraCaptureProps {
  open: boolean;
  onClose: () => void;
  onCapture: (file: File) => void;
}

const SAMPLE_W = 160;
const SAMPLE_H = 120;

export function CameraCapture({ open, onClose, onCapture }: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const detectorRef = useRef<{ detect: (v: HTMLVideoElement) => Promise<FaceBox[]> } | null>(null);
  const guidanceKindRef = useRef<string>("loading");

  const [facing, setFacing] = useState<"user" | "environment">("user");
  const [status, setStatus] = useState<CamStatus>("starting");
  const [error, setError] = useState<string | null>(null);
  const [guidance, setGuidance] = useState<Guidance>({
    kind: "loading",
    title: "Starting camera…",
    hint: "",
    ok: false,
  });
  const [capturing, setCapturing] = useState(false);

  const stopStream = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;

    setStatus("starting");
    setError(null);
    guidanceKindRef.current = "loading";
    setGuidance({ kind: "loading", title: "Starting camera…", hint: "", ok: false });

    loadFaceDetector()
      .then((d) => {
        if (!cancelled) detectorRef.current = d;
      })
      .catch(() => {
        // Face detection is optional — blur + brightness guidance still work.
      });

    async function start() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setStatus("unavailable");
        setError(
          "Your browser can't open the camera. Use a recent browser over HTTPS, or upload a photo instead.",
        );
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: facing, width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(() => {});
        }
        setStatus("active");
      } catch (e) {
        if (cancelled) return;
        const name = e instanceof DOMException ? e.name : "";
        if (name === "NotAllowedError" || name === "SecurityError") {
          setStatus("denied");
          setError("Camera access was blocked. Allow camera permission in your browser, or upload a photo instead.");
        } else if (name === "NotFoundError" || name === "OverconstrainedError") {
          setStatus("error");
          setError("No camera found on this device. Try uploading a photo instead.");
        } else {
          setStatus("error");
          setError("Couldn't start the camera. Try again or upload a photo instead.");
        }
      }
    }

    start();

    return () => {
      cancelled = true;
      stopStream();
    };
  }, [open, facing, stopStream]);

  useEffect(() => {
    if (status !== "active") return;
    let cancelled = false;
    let hasDetectedOnce = false;
    let lastDetect = 0;
    let faces: FaceBox[] = [];

    const canvas = document.createElement("canvas");
    canvas.width = SAMPLE_W;
    canvas.height = SAMPLE_H;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });

    function tick() {
      if (cancelled) return;
      rafRef.current = requestAnimationFrame(tick);

      const v = videoRef.current;
      if (!v || v.readyState < 2 || !v.videoWidth || !ctx) return;

      let blur = 0;
      let brightness = 0;
      try {
        ctx.drawImage(v, 0, 0, SAMPLE_W, SAMPLE_H);
        const img = ctx.getImageData(0, 0, SAMPLE_W, SAMPLE_H);
        blur = computeBlurScore(img.data, SAMPLE_W, SAMPLE_H);
        brightness = computeBrightness(img.data, SAMPLE_W, SAMPLE_H);
      } catch {
        return;
      }

      const now = performance.now();
      const detector = detectorRef.current;
      if (detector && now - lastDetect > 300) {
        lastDetect = now;
        detector
          .detect(v)
          .then((res) => {
            if (cancelled) return;
            faces = res;
            hasDetectedOnce = true;
          })
          .catch(() => {});
      }

      const next = evaluateFrame({
        faces,
        faceDetectionAvailable: Boolean(detector) && hasDetectedOnce,
        blurScore: blur,
        brightness,
      });
      if (next.kind !== guidanceKindRef.current) {
        guidanceKindRef.current = next.kind;
        setGuidance(next);
      }
    }

    rafRef.current = requestAnimationFrame(tick);
    return () => {
      cancelled = true;
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [status]);

  async function capture() {
    const v = videoRef.current;
    if (!v || !v.videoWidth || capturing) return;
    setCapturing(true);
    try {
      const canvas = document.createElement("canvas");
      canvas.width = v.videoWidth;
      canvas.height = v.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("canvas unavailable");
      ctx.drawImage(v, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob(resolve, "image/jpeg", 0.92),
      );
      if (!blob) throw new Error("capture failed");
      onCapture(new File([blob], `camera-${Date.now()}.jpg`, { type: "image/jpeg" }));
    } catch {
      setError("Couldn't capture the photo. Try again or upload instead.");
    } finally {
      setCapturing(false);
    }
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col bg-black"
      role="dialog"
      aria-modal="true"
      aria-label="Camera"
    >
      <div className="flex items-center justify-between px-4 py-3 pt-[max(env(safe-area-inset-top,0px),12px)]">
        <p className="text-sm font-medium text-white">Take a selfie</p>
        <button
          type="button"
          onClick={onClose}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20"
          aria-label="Close camera"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="relative flex-1 overflow-hidden">
        {status === "active" ? (
          <video ref={videoRef} playsInline muted className="h-full w-full object-cover" />
        ) : null}

        {status === "active" ? (
          <div
            className={cn(
              "pointer-events-none absolute inset-x-6 top-6 bottom-44 rounded-3xl border-2 transition-colors",
              guidance.ok ? "border-success" : "border-gold",
            )}
          />
        ) : null}

        {status === "starting" ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-white">
            <Spinner className="h-8 w-8" />
            <p className="text-sm text-white/80">Starting camera…</p>
          </div>
        ) : null}

        {error ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 px-8 text-center text-white">
            <p className="text-sm text-white/90">{error}</p>
            <Button variant="secondary" onClick={onClose}>
              Go back
            </Button>
          </div>
        ) : null}
      </div>

      {status === "active" && !error ? (
        <div className="px-6 pb-3 text-center">
          <p className={cn("text-base font-semibold", guidance.ok ? "text-success" : "text-gold")}>
            {guidance.title}
          </p>
          <p className="mt-1 text-sm text-white/70">{guidance.hint}</p>
        </div>
      ) : null}

      {status === "active" && !error ? (
        <div className="flex items-center justify-center gap-6 px-6 pb-[max(env(safe-area-inset-bottom,0px),20px)]">
          <button
            type="button"
            onClick={() => setFacing((f) => (f === "user" ? "environment" : "user"))}
            className="flex h-12 w-12 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20"
            aria-label="Flip camera"
          >
            <RefreshCw className="h-5 w-5" />
          </button>

          <button
            type="button"
            onClick={capture}
            disabled={capturing}
            className="flex h-16 w-16 items-center justify-center rounded-full border-4 border-white bg-white/20 transition-transform active:scale-95 disabled:opacity-60"
            aria-label="Capture photo"
          >
            <span className="h-12 w-12 rounded-full bg-white" />
          </button>

          <div className="h-12 w-12" aria-hidden />
        </div>
      ) : null}
    </div>
  );
}
