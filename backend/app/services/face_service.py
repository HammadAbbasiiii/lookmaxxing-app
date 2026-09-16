import cv2
import numpy as np
import math
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# ── Scoring sanity thresholds ─────────────────────────────────
# A real face's mirror-pair distance is a small fraction of the image width
# (empirically < 0.1); the old mock ellipse measured ~0.4. Anything above this
# is not a face, so symmetry is reported as "not measured" (None) rather than 0.
MAX_MIRROR_DISTANCE = 0.25
# 100 - 0.25 * 250 = 37.5, so this is belt-and-braces: no real measurement may
# be reported below a plausible floor.
MIN_MEASURABLE_SCORE = 0.0

# ── Resolve MediaPipe model path ──────────────────────────────
_MODEL_FILENAME = "face_landmarker.task"
_MODEL_CANDIDATES = [
    # Render build path (downloaded in buildCommand)
    os.path.join(os.path.dirname(__file__), "..", "ml", _MODEL_FILENAME),
    # Absolute Render path
    f"/opt/render/project/src/backend/app/ml/{_MODEL_FILENAME}",
    # Local development fallback
    os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")), "app", "ml", _MODEL_FILENAME),
]

MODEL_ASSET_PATH = None
for candidate in _MODEL_CANDIDATES:
    # A truncated/empty download (e.g. a build-time curl failure) still "exists"
    # on disk, so require a non-trivial size. The float16 landmarker is ~3.6 MB;
    # anything well under that is a broken/partial download and must not enable
    # MediaPipe (otherwise create_from_options() throws at first use).
    if os.path.exists(candidate) and os.path.getsize(candidate) >= 3_000_000:
        MODEL_ASSET_PATH = candidate
        break

# ── MediaPipe Setup ───────────────────────────────────────────
MEDIAPIPE_AVAILABLE = False
_options = None
_mp_import_error = None

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.vision import FaceLandmarker, FaceLandmarkerOptions
    from mediapipe.tasks.python import BaseOptions

    if MODEL_ASSET_PATH:
        _options = FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_ASSET_PATH),
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            output_face_blendshapes=False,
            running_mode=mp_python.vision.RunningMode.IMAGE,
        )
        MEDIAPIPE_AVAILABLE = True
        print(f"✅ MediaPipe FaceLandmarker ready — model: {MODEL_ASSET_PATH}")
    else:
        _mp_import_error = "model file not found"
        print("⚠️ MediaPipe model file not found. Face landmarks cannot be measured.")
        print(f"   Searched paths: {_MODEL_CANDIDATES}")
        print("   Download: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task")

except Exception as e:
    _mp_import_error = f"mediapipe import failed: {e}"
    print(f"⚠️ MediaPipe initialization error: {e}")
    MEDIAPIPE_AVAILABLE = False


def _unavailable_landmarks_result(reason: str) -> Dict[str, Any]:
    """Result for "MediaPipe can't run right now" — explicitly NOT a success.

    This used to return `success: True` plus 468 *fabricated* ellipse landmarks
    (DEF-014). Callers that checked only `success` — `/photos/analyze/{photo_id}`
    did exactly that — then scored the fake geometry as if it were a real face,
    which is how production stored `symmetry_score = 0`: the pseudo-landmarks
    are not mirror-symmetric, so every mirror pair measured ~0.4 of the image
    width and `100 - 0.4 * 250` clamped to 0, while jawline/eyes happened to land
    in plausible-looking ranges (43 / 37). Fail closed instead: no landmarks, no
    scores. Callers that *do* want a heuristic breakdown must ask for it
    explicitly (see `background_analysis`), never by scoring synthetic geometry.
    """
    return {
        "success": False,
        "landmarks": [],
        "face_count": 0,
        "mock": True,
        "reason": "mediapipe_unavailable",
        "error": reason,
    }


def landmark_measurement(result: Dict[str, Any]) -> str:
    """Classify a `detect_face_landmarks` result: "measured" | "unavailable".

    Single source of truth for every scorer, so a synthetic/degraded result can
    never be mistaken for a measurement again.
    """
    if not result or not result.get("success") or result.get("mock"):
        return "unavailable"
    if len(result.get("landmarks") or []) < 100:
        return "unavailable"
    return "measured"


def unavailable_reason(result: Dict[str, Any]) -> str:
    """Human-readable reason a landmark result is unusable (for logs + UI)."""
    if result and result.get("error"):
        return str(result["error"])
    return "MediaPipe face-landmark model unavailable on this worker"


def mediapipe_status() -> Dict[str, Any]:
    """MediaPipe availability for /health — cheap, no heavy imports.

    Reported from the import-time state of this module (the FaceLandmarker graph
    is still created lazily on first analysis), so a health ping stays ~ms.
    """
    model_exists = bool(MODEL_ASSET_PATH) and os.path.exists(MODEL_ASSET_PATH or "")
    reason = None
    if not _mp_import_error:
        if not model_exists:
            reason = "model file missing"
        elif not MEDIAPIPE_AVAILABLE:
            reason = "mediapipe import failed"
    else:
        reason = _mp_import_error
    return {
        "available": MEDIAPIPE_AVAILABLE and model_exists,
        "model_path": MODEL_ASSET_PATH,
        "model_path_exists": model_exists,
        "reason": reason,
    }


_landmarker = None  # cached MediaPipe FaceLandmarker (created once, reused)


def detect_face_landmarks(image_bytes: bytes) -> Dict[str, Any]:
    """
    Detect facial landmarks from image bytes.
    Returns 468 landmarks with x, y, z coordinates.

    Falls back to mock landmarks when the MediaPipe model file is missing OR
    the host lacks the free memory to create its graph safely.
    """
    global _landmarker

    if not MEDIAPIPE_AVAILABLE or _options is None:
        print("📷 No face landmarks: MediaPipe model unavailable (not fabricating scores)")
        return _unavailable_landmarks_result(
            _mp_import_error or "MediaPipe face-landmark model unavailable"
        )

    # On a 512 MB Render worker, creating the MediaPipe graph can OOM-kill
    # the process. Report "unavailable" instead of crashing.
    from app.services.memory_guard import can_load_mediapipe
    if not can_load_mediapipe():
        print("📷 No face landmarks: insufficient free memory for MediaPipe")
        return _unavailable_landmarks_result(
            "Not enough free memory on this worker to load the face-landmark model"
        )

    # Real MediaPipe detection with downloaded model
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"success": False, "error": "Could not decode image"}

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)

        if _landmarker is None:
            _landmarker = FaceLandmarker.create_from_options(_options)
        results = _landmarker.detect(mp_image)

        if not results.face_landmarks:
            msg = "MediaPipe found no face in this image"
            logger.warning(msg)
            return {"success": False, "error": msg}

        landmarks = []
        for landmark in results.face_landmarks[0]:
            landmarks.append({
                "x": landmark.x,
                "y": landmark.y,
                "z": landmark.z
            })

        return {
            "success": True,
            "landmarks": landmarks,
            "face_count": len(results.face_landmarks)
        }
    except Exception as e:
        logger.warning(f"MediaPipe detection error: {e}")
        return {"success": False, "error": f"MediaPipe error: {str(e)}"}


def calculate_symmetry(landmarks: list) -> Optional[float]:
    """
    Calculate facial symmetry score (0-100), or None when it cannot be measured.

    Compares mirrored landmarks across the vertical midline. A real face always
    has *some* symmetry: the mirror distance between MediaPipe's symmetric pairs
    is a fraction of the inter-ocular distance, so the score lands in the 70-100
    band. A value of 0 means the input geometry was not a face at all (this is
    how the old mock ellipse scored — see `_unavailable_landmarks_result`), so we
    return None for "not measured" rather than persisting a 0 that reads as
    "your face is 0% symmetric" (DEF-014).
    """
    if not landmarks or len(landmarks) < 20:
        return None

    symmetry_pairs = [
        (33, 263),    # Eye corners
        (133, 362),   # Eye centers
        (54, 284),    # Eyebrows
        (61, 291),    # Mouth corners
        (152, 377),   # Chin
        (21, 251),    # Nose
    ]

    distances = []
    for left_idx, right_idx in symmetry_pairs:
        if left_idx < len(landmarks) and right_idx < len(landmarks):
            left = landmarks[left_idx]
            right = landmarks[right_idx]

            mirrored_x = 1.0 - right["x"]
            dx = left["x"] - mirrored_x
            dy = left["y"] - right["y"]
            distance = math.sqrt(dx**2 + dy**2)
            distances.append(distance)

    if not distances:
        return None

    avg_distance = sum(distances) / len(distances)
    # Sanity gate: an average mirror distance above MAX_MIRROR_DISTANCE means the
    # "landmarks" are not a human face (real faces measure well under 0.1), so
    # refuse to report a score instead of clamping a garbage input to 0.
    if avg_distance > MAX_MIRROR_DISTANCE:
        logger.warning(
            "Symmetry not measured: implausible landmark geometry "
            f"(avg mirror distance {avg_distance:.3f} > {MAX_MIRROR_DISTANCE})"
        )
        return None

    score = max(0.0, min(100.0, 100 - (avg_distance * 250)))
    if score <= MIN_MEASURABLE_SCORE:
        return None
    return round(score, 1)


def calculate_skin_score(landmarks: list, image_bytes: bytes) -> float:
    """
    Estimate skin quality based on color consistency.
    Uses OpenCV to analyze skin region color variance.
    """
    if not image_bytes:
        return 70.0

    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)

        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)

        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        skin_pixels = cv2.bitwise_and(img_rgb, img_rgb, mask=mask)

        if np.sum(mask) == 0:
            return 70.0

        skin_rgb = img_rgb[mask > 0]
        if len(skin_rgb) < 10:
            return 70.0

        std_r = np.std(skin_rgb[:, 0])
        std_g = np.std(skin_rgb[:, 1])
        std_b = np.std(skin_rgb[:, 2])
        avg_std = (std_r + std_g + std_b) / 3.0

        score = max(0, min(100, 100 - (avg_std / 30.0) * 30))
        return round(score, 1)
    except Exception:
        return 70.0


def calculate_jawline_score(landmarks: list) -> float:
    """Calculate jawline definition score based on jaw landmark geometry."""
    jaw_indices = list(range(172, 183)) + list(range(199, 217)) + list(range(233, 245))
    if not landmarks:
        return 70.0

    jaw_points = [landmarks[i] for i in jaw_indices if i < len(landmarks)]
    if len(jaw_points) < 8:
        return 70.0

    y_values = [p["y"] for p in jaw_points]
    x_values = [p["x"] for p in jaw_points]
    jaw_width = max(x_values) - min(x_values)
    jaw_height = max(y_values) - min(y_values)
    if jaw_height == 0:
        return 70.0

    ratio = jaw_width / jaw_height
    score = 100 - (abs(ratio - 1.7) * 50)
    score = max(0, min(100, score))

    corners = jaw_points[0:2] + jaw_points[-2:]
    corner_depths = [abs(p["z"]) for p in corners]
    definition_bonus = min(10, sum(corner_depths) * 500)

    return round(min(100, score + definition_bonus), 1)


def calculate_eye_score(landmarks: list) -> float:
    """Calculate eye symmetry and horizontal alignment score."""
    left_indices = [33, 133, 160, 159, 158, 157, 173]
    right_indices = [362, 263, 387, 386, 385, 384, 398]

    if len(landmarks) < 400:
        return 75.0

    left_eyes = [landmarks[i] for i in left_indices if i < len(landmarks)]
    right_eyes = [landmarks[i] for i in right_indices if i < len(landmarks)]

    if len(left_eyes) < 3 or len(right_eyes) < 3:
        return 75.0

    left_center_y = sum(p["y"] for p in left_eyes) / len(left_eyes)
    right_center_y = sum(p["y"] for p in right_eyes) / len(right_eyes)

    y_diff = abs(left_center_y - right_center_y)
    alignment_score = max(0, min(100, 100 - (y_diff * 150)))

    left_width = max(p["x"] for p in left_eyes) - min(p["x"] for p in left_eyes)
    right_width = max(p["x"] for p in right_eyes) - min(p["x"] for p in right_eyes)

    if right_width > 0:
        size_ratio = min(left_width, right_width) / max(left_width, right_width)
        size_score = size_ratio * 100
    else:
        size_score = 75.0

    final_score = (alignment_score * 0.6 + size_score * 0.4)
    return round(final_score, 1)


def generate_overall_score(scores: Dict[str, float]) -> float:
    """Generate overall attractiveness score (0-100). Weighted combination."""
    weights = {
        "symmetry": 0.30,
        "skin": 0.20,
        "jawline": 0.20,
        "eyes": 0.15,
        "nose": 0.10,
        "lips": 0.05
    }
    weighted_score = sum(scores.get(key, 70.0) * weight for key, weight in weights.items())
    return round(weighted_score, 1)


def get_face_shape(landmarks: list) -> str:
    """Determine face shape from jaw and forehead landmarks."""
    if not landmarks:
        return "Unknown"

    jaw_indices = list(range(172, 183)) + list(range(199, 217)) + list(range(233, 245))
    forehead_indices = list(range(10, 20)) + list(range(108, 112))

    jaw_points = [landmarks[i] for i in jaw_indices if i < len(landmarks)]
    forehead_points = [landmarks[i] for i in forehead_indices if i < len(landmarks)]

    if len(jaw_points) < 10:
        return "Oval"

    jaw_y = [p["y"] for p in jaw_points]
    jaw_x = [p["x"] for p in jaw_points]
    jaw_width = max(jaw_x) - min(jaw_x)
    jaw_height = max(jaw_y) - min(jaw_y)

    forehead_width = 0.3
    if forehead_points:
        forehead_x = [p["x"] for p in forehead_points]
        forehead_width = max(forehead_x) - min(forehead_x)

    if jaw_height == 0:
        return "Oval"

    ratio = jaw_width / jaw_height

    if forehead_width > jaw_width * 1.1 and ratio < 1.4:
        return "Heart"
    elif ratio < 1.2:
        return "Round"
    elif ratio < 1.5:
        return "Oval"
    elif ratio < 1.8:
        return "Square"
    else:
        return "Diamond"