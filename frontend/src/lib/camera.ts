// Live camera guidance helpers for the in-app camera capture flow.
// Blur (Laplacian variance) and brightness run entirely in the browser with no
// dependencies. Face framing uses MediaPipe FaceDetector, lazy-loaded at runtime
// so the rest of the app never pays its bundle/startup cost.

import type { FaceDetector as MediaPipeFaceDetector } from "@mediapipe/tasks-vision";

export type GuidanceKind =
  | "loading"
  | "no-face"
  | "multiple-faces"
  | "too-far"
  | "too-close"
  | "off-center"
  | "blurry"
  | "low-light"
  | "ready";

export interface Guidance {
  kind: GuidanceKind;
  title: string;
  hint: string;
  /** True when the shot is good enough to capture. */
  ok: boolean;
}

export interface FaceBox {
  /** Normalized 0..1 relative to the video frame dimensions. */
  originX: number;
  originY: number;
  width: number;
  height: number;
}

/** Laplacian variance below this reads as "blurry" (0–255 grayscale). */
export const BLUR_THRESHOLD = 100;
/** Mean luminance below this reads as "too dark" for a usable selfie. */
export const LOW_LIGHT_THRESHOLD = 40;

// Face-framing thresholds (normalized to frame width / center offset).
const TOO_FAR_MAX_WIDTH = 0.18;
const TOO_CLOSE_MIN_WIDTH = 0.62;
const CENTER_TOLERANCE = 0.16;

/** Sharpness via variance of the Laplacian over a downsampled frame. */
export function computeBlurScore(data: Uint8ClampedArray, width: number, height: number): number {
  const gray = new Float32Array(width * height);
  for (let i = 0; i < width * height; i++) {
    const o = i * 4;
    gray[i] = 0.299 * data[o] + 0.587 * data[o + 1] + 0.114 * data[o + 2];
  }
  let sum = 0;
  let sumSq = 0;
  let n = 0;
  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const idx = y * width + x;
      const lap =
        gray[idx - width] + gray[idx + width] + gray[idx - 1] + gray[idx + 1] - 4 * gray[idx];
      sum += lap;
      sumSq += lap * lap;
      n++;
    }
  }
  if (n === 0) return 0;
  const mean = sum / n;
  return sumSq / n - mean * mean;
}

/** Mean luminance of a frame (0–255). */
export function computeBrightness(data: Uint8ClampedArray, width: number, height: number): number {
  let sum = 0;
  const n = width * height;
  for (let i = 0; i < n; i++) {
    const o = i * 4;
    sum += 0.299 * data[o] + 0.587 * data[o + 1] + 0.114 * data[o + 2];
  }
  return n === 0 ? 0 : sum / n;
}

/** Combine blur, brightness, and face framing into a single live instruction. */
export function evaluateFrame(params: {
  faces: FaceBox[];
  faceDetectionAvailable: boolean;
  blurScore: number;
  brightness: number;
}): Guidance {
  const { faces, faceDetectionAvailable, blurScore, brightness } = params;

  // Blur + lighting apply regardless of face detection.
  if (blurScore < BLUR_THRESHOLD) {
    return {
      kind: "blurry",
      title: "Looks a bit blurry",
      hint: "Hold the camera still and get more light on your face.",
      ok: false,
    };
  }
  if (brightness < LOW_LIGHT_THRESHOLD) {
    return {
      kind: "low-light",
      title: "It's a bit dark",
      hint: "Find brighter light so we can see your features clearly.",
      ok: false,
    };
  }

  // Without a face detector loaded, give neutral framing guidance only.
  if (!faceDetectionAvailable) {
    return {
      kind: "ready",
      title: "Look straight at the camera",
      hint: "Keep your face well-lit and centred, then capture.",
      ok: true,
    };
  }

  if (faces.length === 0) {
    return {
      kind: "no-face",
      title: "No face found",
      hint: "Look straight at the camera and fit your whole face in the frame.",
      ok: false,
    };
  }
  if (faces.length > 1) {
    return {
      kind: "multiple-faces",
      title: "One face at a time",
      hint: "Make sure you're the only person in the shot.",
      ok: false,
    };
  }

  const box = faces[0];
  const centerX = box.originX + box.width / 2;
  const centerY = box.originY + box.height / 2;

  if (box.width < TOO_FAR_MAX_WIDTH) {
    return {
      kind: "too-far",
      title: "Move a little closer",
      hint: "Your face is small in the frame — step closer until it fills more of the screen.",
      ok: false,
    };
  }
  if (box.width > TOO_CLOSE_MIN_WIDTH) {
    return {
      kind: "too-close",
      title: "Move back a touch",
      hint: "You're a bit close — pull back so your whole face fits comfortably.",
      ok: false,
    };
  }
  if (Math.abs(centerX - 0.5) > CENTER_TOLERANCE || Math.abs(centerY - 0.5) > CENTER_TOLERANCE) {
    return {
      kind: "off-center",
      title: "Center your face",
      hint: "Move so your face sits in the middle of the frame.",
      ok: false,
    };
  }

  return {
    kind: "ready",
    title: "Perfect — you're good",
    hint: "Tap the shutter to take the photo.",
    ok: true,
  };
}

// ── MediaPipe face detector (lazy) ──────────────────────────────────

interface DetectorHandle {
  detect: (video: HTMLVideoElement) => Promise<FaceBox[]>;
}

let detectorPromise: Promise<DetectorHandle> | null = null;

export function loadFaceDetector(): Promise<DetectorHandle> {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Face detection only runs in the browser."));
  }
  if (!detectorPromise) {
    detectorPromise = createDetector().catch((err) => {
      detectorPromise = null; // allow a retry on the next open
      throw err;
    });
  }
  return detectorPromise;
}

async function createDetector(): Promise<DetectorHandle> {
  const vision = await import("@mediapipe/tasks-vision");
  const fileset = await vision.FilesetResolver.forVisionTasks(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm",
  );

  const delegates: Array<"GPU" | "CPU"> = ["GPU", "CPU"];
  let detector: MediaPipeFaceDetector | null = null;
  for (const delegate of delegates) {
    try {
      detector = await vision.FaceDetector.createFromOptions(fileset, {
        baseOptions: {
          modelAssetPath:
            "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite",
          delegate,
        },
        runningMode: "VIDEO",
      });
      break;
    } catch {
      // fall through to the next delegate
    }
  }
  if (!detector) throw new Error("Face detector failed to initialize.");
  const faceDetector = detector;

  return {
    detect: async (video: HTMLVideoElement) => {
      const result = faceDetector.detectForVideo(video, performance.now());
      const w = video.videoWidth || 1;
      const h = video.videoHeight || 1;
      return (result.detections ?? []).map((d) => ({
        originX: (d.boundingBox?.originX ?? 0) / w,
        originY: (d.boundingBox?.originY ?? 0) / h,
        width: (d.boundingBox?.width ?? 0) / w,
        height: (d.boundingBox?.height ?? 0) / h,
      }));
    },
  };
}
