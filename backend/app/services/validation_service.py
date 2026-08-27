"""
Image pre-validation service.

Runs BEFORE any AI analysis. Rejects unusable images (no face, blurry,
too dark/bright, wrong size) with clear, user-facing messages so the app
never wastes an AI pass — or returns a nonsense score — for a flower, a
blurry selfie, or a pitch-black photo.

This is the gate that runs before `run_analysis_background` does any
prediction / landmark / plan work.
"""
import io
import logging

import cv2
import numpy as np
from PIL import Image

from app.services.face_service import MEDIAPIPE_AVAILABLE, detect_face_landmarks

logger = logging.getLogger(__name__)

# ── Tunables ──────────────────────────────────────────────────────────────
MIN_DIMENSION = 150
MAX_DIMENSION = 5000
MIN_BRIGHTNESS = 40.0     # mean grayscale value — below this = too dark
MAX_BRIGHTNESS = 230.0    # mean grayscale value — above this = too bright
MIN_CONTRAST = 25.0       # std-dev of grayscale pixels
MIN_BLUR_SCORE = 50.0     # Laplacian variance — below this = blurry
MIN_FACE_RATIO = 0.05     # face bounding-box area / image area


def validate_image(image_bytes: bytes) -> dict:
    """Run pre-analysis quality checks on an image.

    Returns:
        {"valid": bool, "error": str | None}
    """
    # ── Decode & size ────────────────────────────────────────────────────
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return {"valid": False, "error": "Could not read this image. Please choose a different photo."}

    w, h = img.size
    if w < MIN_DIMENSION or h < MIN_DIMENSION:
        return {"valid": False, "error": "Image is too small. Please use a photo at least 150×150 pixels."}
    if w > MAX_DIMENSION or h > MAX_DIMENSION:
        return {"valid": False, "error": "Image is too large. Please use a smaller photo."}

    # ── Brightness / contrast / blur ─────────────────────────────────────
    gray = np.array(img.convert("L"))
    brightness = float(gray.mean())
    contrast = float(gray.std())
    blur = float(cv2.Laplacian(gray.astype(np.float32), cv2.CV_32F).var())

    if brightness < MIN_BRIGHTNESS:
        return {"valid": False, "error": "Photo is too dark. Please retake it in good lighting."}
    if brightness > MAX_BRIGHTNESS:
        return {"valid": False, "error": "Photo is too bright. Please move to a more even, shaded area."}
    if contrast < MIN_CONTRAST:
        return {"valid": False, "error": "Photo contrast is too low. Please use better lighting."}
    if blur < MIN_BLUR_SCORE:
        return {"valid": False, "error": "Photo is blurry. Please hold the camera steady and retake it."}

    # ── Face presence & size ─────────────────────────────────────────────
    face_found, face_ratio = _detect_face(image_bytes, w, h)
    if not face_found:
        return {"valid": False, "error": "No face detected. Please use a clear, front-facing photo of your face."}
    if face_ratio is not None and face_ratio < MIN_FACE_RATIO:
        return {"valid": False, "error": "Your face is too small in the frame. Please move closer and retake it."}

    return {"valid": True, "error": None}


def _detect_face(image_bytes, w, h):
    """Return (face_found, face_ratio) using strict detection (never mock)."""
    # 1) MediaPipe (real landmarker) — preferred, most accurate.
    if MEDIAPIPE_AVAILABLE:
        try:
            result = detect_face_landmarks(image_bytes)
            if result.get("success") and result.get("landmarks"):
                return True, _landmarks_ratio(result["landmarks"], w, h)
            return False, None
        except Exception as exc:
            logger.warning(f"MediaPipe face validation failed: {exc}")

    # 2) OpenCV Haar cascade — always available, no model file needed.
    nparr = np.frombuffer(image_bytes, np.uint8)
    bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if bgr is None:
        return False, None
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if cascade.empty():
        # Fail-open: without any detector we cannot verify a face, so don't
        # block every upload on a missing model file.
        logger.warning("Haar cascade unavailable — skipping face validation")
        return True, None
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
    if len(faces) == 0:
        return False, None
    fx, fy, fw, fh = max(faces, key=lambda r: r[2] * r[3])
    return True, (fw * fh) / float(w * h)


def _landmarks_ratio(landmarks, w, h):
    """Approximate face area ratio from (usually normalized) landmarks."""
    xs = [p.get("x") for p in landmarks if p.get("x") is not None]
    ys = [p.get("y") for p in landmarks if p.get("y") is not None]
    if not xs or not ys:
        return None
    if max(xs) <= 1.0 and max(ys) <= 1.0:
        face_w = (max(xs) - min(xs)) * w
        face_h = (max(ys) - min(ys)) * h
    else:
        face_w = max(xs) - min(xs)
        face_h = max(ys) - min(ys)
    area = w * h
    return (face_w * face_h) / area if area else 0.0
