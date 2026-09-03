"""
Face Analysis Service - Category Breakdown System
Calculates 6 category scores from facial landmarks and image properties.
Each category returns a score (0-100) and a description label.
"""
import cv2
import numpy as np
import math
import os
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MediaPipe landmark extraction
# ---------------------------------------------------------------------------
# There is exactly ONE MediaPipe FaceLandmarker graph in the process, owned by
# face_service.py. Loading a second graph here (as this module used to do at
# import time) doubled MediaPipe's ~500 MB footprint on Render and caused the
# second graph to fail after torch loaded, which left category_breakdown empty.
# All landmark extraction now delegates to the shared loader.
from app.services.face_service import MEDIAPIPE_AVAILABLE, detect_face_landmarks


def is_mediapipe_available() -> bool:
    """Return whether the shared MediaPipe FaceLandmarker is available."""
    return MEDIAPIPE_AVAILABLE


def get_mediapipe_status() -> dict:
    """Return MediaPipe status for health checks (delegates to face_service)."""
    return {
        "available": MEDIAPIPE_AVAILABLE,
        "model_path": None,
        "model_path_exists": MEDIAPIPE_AVAILABLE,
        "error": None if MEDIAPIPE_AVAILABLE else "MediaPipe model not loaded (see face_service)",
    }

# ---------------------------------------------------------------------------
# MediaPipe landmark indices (FaceMesh topology)
# ---------------------------------------------------------------------------
# Jawline (oval from chin to ears)
JAW_INDICES = [0, 17, 37, 39, 40, 61, 81, 82, 84, 87, 88, 91, 95, 146, 149, 150, 152,
               172, 176, 177, 178, 181, 185, 199, 200, 204, 206, 207, 211, 212, 216,
               263, 267, 269, 270, 291, 308, 309, 310, 311, 314, 317, 318, 321, 324,
               325, 332, 334, 338, 356, 365, 367, 368, 373, 374, 375, 376, 377, 379,
               380, 381, 382, 384, 385, 386, 387, 388, 389, 390, 397, 400, 402, 405,
               409, 415, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441, 442,
               444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454]

# Eyes (left and right)
LEFT_EYE = [33, 133, 155, 154, 153, 145, 144, 163, 7, 173, 157, 158, 159, 160, 161, 246]
RIGHT_EYE = [362, 263, 382, 381, 380, 374, 373, 390, 249, 398, 384, 385, 386, 387, 388, 466]

# Eyebrows
LEFT_BROW = [46, 53, 52, 65, 55, 70, 63, 105, 66, 107]
RIGHT_BROW = [276, 283, 282, 295, 285, 300, 293, 334, 296, 336]

# Nose
NOSE_BRIDGE = [168, 6, 197, 195, 5, 4, 1, 19, 94, 2]
NOSE_TIP = [1, 2, 3, 4, 5, 19, 94, 248, 456, 278, 437, 343, 412, 351, 419]

# Cheekbones (zygomatic arch)
LEFT_CHEEK = [50, 117, 118, 119, 47, 101, 36, 203, 205, 187, 123, 50]
RIGHT_CHEEK = [280, 346, 347, 348, 277, 330, 266, 423, 425, 411, 352, 280]

# Midline
MIDLINE_TOP = 10       # Top of forehead
MIDLINE_CHIN = 152     # Bottom of chin
MIDLINE_NOSE_BRIDGE = 6  # Nose bridge

# ---------------------------------------------------------------------------
# Landmark extraction
# ---------------------------------------------------------------------------
def extract_face_landmarks(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extract 468 facial landmarks using the shared MediaPipe FaceLandmarker.

    Delegates to face_service.detect_face_landmarks so there is exactly one
    MediaPipe graph in the process (avoids double-loading ~500 MB on Render).

    Returns:
        dict with success (bool), landmarks (list of {x, y, z}), face_count (int),
        and optional mock (bool) if fallback was used.
    """
    return detect_face_landmarks(image_bytes)


def _generate_mock_landmarks() -> List[Dict[str, float]]:
    """Generate 468 mock landmarks that approximate a realistic human face topology.

    These mimic the MediaPipe FaceMesh landmark layout so category functions
    produce reasonable scores even when MediaPipe is unavailable.

    Face region seed coordinates (normalised 0-1, origin top-left):
      0.50,0.15  - hairline (landmark 10)
      0.50,0.85  - chin     (landmark 152)
      0.35,0.55  - left cheekbone (landmark 123)
      0.65,0.55  - right cheekbone (landmark 352)
      0.40,0.62  - left jaw angle  (landmark 172)
      0.60,0.62  - right jaw angle (landmark 397)
      0.37,0.45  - left eye center
      0.63,0.45  - right eye center
      0.42,0.40  - left eyebrow center
      0.58,0.40  - right eyebrow
      0.50,0.52  - nose tip (landmark 2)
      0.50,0.58  - upper lip (landmark 13)
    """

    # ---- Helper: interpolate between points ----
    def lerp(a: Tuple[float, float], b: Tuple[float, float], t: float) -> Tuple[float, float]:
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

    def pt(x: float, y: float, z: float = 0.0) -> Dict[str, float]:
        return {"x": round(x, 6), "y": round(y, 6), "z": round(z, 6)}

    landmarks: List[Optional[Dict[str, float]]] = [None] * 468

    # ---- Build jawline / oval contour (landmarks 0-16, plus additional contour indices) ----
    # Left-to-right jawline arc
    jaw_contour = [
        (0,   0.50, 0.15),   # top centre
        (1,   0.42, 0.17),
        (2,   0.34, 0.21),
        (3,   0.28, 0.26),
        (4,   0.24, 0.32),
        (5,   0.21, 0.38),
        (6,   0.20, 0.44),
        (7,   0.20, 0.50),
        (8,   0.21, 0.56),
        (9,   0.24, 0.62),
        (10,  0.28, 0.68),   # left jaw
        (11,  0.34, 0.74),
        (12,  0.40, 0.78),
        (13,  0.46, 0.82),
        (14,  0.50, 0.84),   # chin
        (15,  0.54, 0.82),
        (16,  0.60, 0.78),
        # remaining contour points follow right side mirror
    ]
    for idx, x, y in jaw_contour:
        landmarks[idx] = pt(x, y)

    # ---- Left eye region (around landmarks 33, 133, 159, 157, 158, 173, 145, 144, 163, 7, 246) ----
    leye_x, leye_y = 0.365, 0.45
    # Eye outline  - small oval
    leye_pts = [(33, leye_x - 0.022, leye_y),
                (133, leye_x + 0.022, leye_y),
                (159, leye_x, leye_y - 0.010),
                (158, leye_x + 0.005, leye_y - 0.005),
                (157, leye_x - 0.005, leye_y - 0.005),
                (173, leye_x + 0.005, leye_y + 0.008),
                (145, leye_x - 0.005, leye_y + 0.008),
                (144, leye_x - 0.010, leye_y + 0.004),
                (163, leye_x + 0.010, leye_y + 0.004),
                (7, leye_x, leye_y - 0.002),
                (246, leye_x, leye_y + 0.002),
                (155, leye_x - 0.018, leye_y - 0.004),
                (154, leye_x + 0.018, leye_y + 0.004),
                (153, leye_x + 0.020, leye_y),
                (160, leye_x - 0.020, leye_y),
                (161, leye_x + 0.015, leye_y + 0.006),
    ]
    for idx, x, y in leye_pts:
        landmarks[idx] = pt(x, y)

    # ---- Right eye region (mirror of left around 0.5) ----
    reye_x, reye_y = 0.635, 0.45
    reye_pts = [(362, reye_x - 0.022, reye_y),
                (263, reye_x + 0.022, reye_y),
                (386, reye_x, reye_y - 0.010),
                (385, reye_x + 0.005, reye_y - 0.005),
                (384, reye_x - 0.005, reye_y - 0.005),
                (398, reye_x + 0.005, reye_y + 0.008),
                (374, reye_x - 0.005, reye_y + 0.008),
                (373, reye_x - 0.010, reye_y + 0.004),
                (390, reye_x + 0.010, reye_y + 0.004),
                (249, reye_x, reye_y - 0.002),
                (466, reye_x, reye_y + 0.002),
                (382, reye_x + 0.018, reye_y - 0.004),
                (381, reye_x - 0.018, reye_y + 0.004),
                (380, reye_x - 0.020, reye_y),
                (387, reye_x + 0.020, reye_y),
                (388, reye_x - 0.015, reye_y + 0.006),
    ]
    for idx, x, y in reye_pts:
        landmarks[idx] = pt(x, y)

    # ---- Left eyebrow ----
    lbx, lby = 0.355, 0.40
    lbrow_pts = [(46, lbx - 0.025, lby),
                 (53, lbx - 0.015, lby - 0.003),
                 (52, lbx - 0.005, lby - 0.005),
                 (65, lbx + 0.005, lby - 0.005),
                 (55, lbx + 0.015, lby - 0.003),
                 (70, lbx + 0.025, lby),
                 (63, lbx + 0.020, lby + 0.003),
                 (105, lbx - 0.020, lby + 0.003),
                 (66, lbx + 0.012, lby - 0.001),
                 (107, lbx - 0.012, lby - 0.001),
    ]
    for idx, x, y in lbrow_pts:
        landmarks[idx] = pt(x, y)

    # ---- Right eyebrow ----
    rbx, rby = 0.645, 0.40
    rbrow_pts = [(276, rbx - 0.025, rby),
                 (283, rbx - 0.015, rby - 0.003),
                 (282, rbx - 0.005, rby - 0.005),
                 (295, rbx + 0.005, rby - 0.005),
                 (285, rbx + 0.015, rby - 0.003),
                 (300, rbx + 0.025, rby),
                 (293, rbx + 0.020, rby + 0.003),
                 (334, rbx - 0.020, rby + 0.003),
                 (296, rbx + 0.012, rby - 0.001),
                 (336, rbx - 0.012, rby - 0.001),
    ]
    for idx, x, y in rbrow_pts:
        landmarks[idx] = pt(x, y)

    # ---- Nose bridge + tip ----
    nose_pts = [
        (6, 0.50, 0.40),    # bridge
        (197, 0.50, 0.43),
        (195, 0.50, 0.46),
        (5, 0.50, 0.49),
        (4, 0.50, 0.51),
        (1, 0.50, 0.53),
        (2, 0.50, 0.545),   # tip
        (19, 0.50, 0.547),
        (94, 0.50, 0.55),
        (168, 0.50, 0.38),
        (248, 0.51, 0.545),  # right of tip
        (456, 0.49, 0.545),  # left of tip
        (278, 0.52, 0.54),
        (437, 0.48, 0.54),
        (343, 0.515, 0.535),
        (412, 0.485, 0.535),
        (351, 0.505, 0.538),
        (419, 0.495, 0.538),
    ]
    for idx, x, y in nose_pts:
        landmarks[idx] = pt(x, y)

    # ---- Nose ala (nostrils) ----
    landmarks[64] = pt(0.45, 0.535)   # left nostril
    landmarks[294] = pt(0.55, 0.535)  # right nostril

    # ---- Cheekbones ----
    cheek_pts = [
        (123, 0.36, 0.56),   # left
        (352, 0.64, 0.56),   # right
        (50, 0.38, 0.59),
        (280, 0.62, 0.59),
        (117, 0.34, 0.54),
        (346, 0.66, 0.54),
        (118, 0.33, 0.52),
        (347, 0.67, 0.52),
        (119, 0.32, 0.50),
        (348, 0.68, 0.50),
        (47, 0.35, 0.48),
        (277, 0.65, 0.48),
        (101, 0.31, 0.46),
        (330, 0.69, 0.46),
        (36, 0.30, 0.44),
        (266, 0.70, 0.44),
        (203, 0.33, 0.42),
        (423, 0.67, 0.42),
        (205, 0.34, 0.45),
        (425, 0.66, 0.45),
        (187, 0.37, 0.53),
        (411, 0.63, 0.53),
    ]
    for idx, x, y in cheek_pts:
        landmarks[idx] = pt(x, y)

    # ---- Jaw angles (gonion) ----
    landmarks[172] = pt(0.39, 0.70)   # left jaw angle
    landmarks[397] = pt(0.61, 0.70)   # right jaw angle

    # ---- Forehead corners ----
    landmarks[10] = pt(0.50, 0.15)    # top of forehead
    landmarks[54] = pt(0.38, 0.18)    # left forehead
    landmarks[284] = pt(0.62, 0.18)   # right forehead

    # ---- Chin ----
    landmarks[152] = pt(0.50, 0.84)

    # ---- Lips / mouth region ----
    landmarks[13] = pt(0.50, 0.58)    # between lips
    landmarks[14] = pt(0.50, 0.59)    # lower lip center
    landmarks[0] = pt(0.50, 0.155)    # top centre (overwrite with hairline)

    # ---- Fill remaining landmarks via interpolation for completeness ----
    # For any unfilled landmark, place it at a sensible location near its region
    remaining = [i for i in range(468) if landmarks[i] is None]
    for idx in remaining:
        # Place at nearest known landmark or a safe default
        if idx < 17:  # jaw contour holdouts
            t = idx / 16.0
            landmarks[idx] = pt(0.50 + 0.28 * math.cos(t * math.pi * 2 - math.pi / 2),
                                0.50 + 0.34 * math.sin(t * math.pi * 2 - math.pi / 2))
        elif 17 <= idx < 200:  # left/centre face
            landmarks[idx] = pt(0.40, 0.50, 0.005)
        else:  # right face
            landmarks[idx] = pt(0.60, 0.50, -0.005)

    # Ensure all 468 are present
    return [lm if lm is not None else pt(0.50, 0.50, 0.0) for lm in landmarks]


# ---------------------------------------------------------------------------
# Category 1: Facial Harmony (symmetry + proportion)
# ---------------------------------------------------------------------------
def calculate_facial_harmony(landmarks: List[Dict]) -> Tuple[float, str]:
    """
    Calculate facial harmony based on bilateral symmetry and proportional ratios.

    Returns (score 0-100, description label).
    """
    if not landmarks or len(landmarks) < 468:
        return 70.0, "Adequate"

    # --- Symmetry (left vs right) ---
    # Use exact MediaPipe symmetric pairs
    symmetry_pairs = [
        (33, 263), (133, 362), (159, 386), (158, 385), (157, 384),
        (173, 398), (46, 276), (53, 283), (105, 334), (66, 296),
        (61, 291), (40, 270), (37, 267), (39, 269), (17, 0),
        (130, 359), (243, 463), (117, 346), (118, 347), (119, 348),
    ]

    symmetry_dists = []
    for l_idx, r_idx in symmetry_pairs:
        if l_idx < len(landmarks) and r_idx < len(landmarks):
            l = landmarks[l_idx]
            r = landmarks[r_idx]
            mirrored_x = 1.0 - r["x"]
            dist = math.sqrt((l["x"] - mirrored_x) ** 2 + (l["y"] - r["y"]) ** 2)
            symmetry_dists.append(dist)

    if symmetry_dists:
        avg_sym_dist = sum(symmetry_dists) / len(symmetry_dists)
        symmetry_score = max(0, min(100, 100 - avg_sym_dist * 250))
    else:
        symmetry_score = 70.0

    # --- Golden ratio check: face width / face height ---
    # Width between cheekbones (approx)
    if 234 < len(landmarks):
        left_cheek_x = landmarks[123]["x"]
        right_cheek_x = landmarks[352]["x"]
        face_width = abs(right_cheek_x - left_cheek_x)

        # Height from hairline to chin
        hairline_y = landmarks[10]["y"]
        chin_y = landmarks[152]["y"]
        face_height = abs(chin_y - hairline_y)

        if face_height > 0:
            ratio = face_width / face_height
            # Ideal width/height ratio ~ 0.75-0.8 for an oval face
            ratio_score = 100 - abs(ratio - 0.78) * 150
            ratio_score = max(0, min(100, ratio_score))
        else:
            ratio_score = 70.0
    else:
        ratio_score = 70.0

    # Combine symmetry + ratio
    final = symmetry_score * 0.6 + ratio_score * 0.4

    # Description
    if final >= 80:
        desc = "Exceptional balance and proportion"
    elif final >= 65:
        desc = "Good symmetry with pleasing proportions"
    elif final >= 50:
        desc = "Adequate balance, room for refinement"
    elif final >= 35:
        desc = "Noticeable imbalance in some areas"
    else:
        desc = "Significant asymmetry — focus on balancing features"

    return round(final, 1), desc


# ---------------------------------------------------------------------------
# Category 2: Skin Quality (brightness, contrast, texture)
# ---------------------------------------------------------------------------
def calculate_skin_quality(image_bytes: bytes) -> Tuple[float, str]:
    """
    Estimate skin quality from image brightness, contrast, and texture uniformity.

    Returns (score 0-100, description label).
    """
    if not image_bytes:
        return 70.0, "Unable to assess"

    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return 70.0, "Unable to assess"

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

        # --- Brightness ---
        mean_brightness = np.mean(gray) / 255.0  # 0-1 range
        # Ideal brightness ~0.45-0.6 (not too dark, not washed out)
        if 0.4 <= mean_brightness <= 0.65:
            brightness_score = 100.0
        else:
            brightness_score = 100 - abs(mean_brightness - 0.5) * 200
            brightness_score = max(20, min(100, brightness_score))

        # --- Contrast (standard deviation) ---
        contrast_std = np.std(gray)
        # Good contrast std ~45-70 for 8-bit images
        if 40 <= contrast_std <= 75:
            contrast_score = 100.0
        elif contrast_std < 25:
            contrast_score = contrast_std / 25 * 60  # Very flat
        else:
            contrast_score = 100 - min(40, abs(contrast_std - 57) * 1.5)
        contrast_score = max(20, min(100, contrast_score))

        # --- Texture (local variance on skin-like regions) ---
        hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)
        lower = np.array([0, 15, 40], dtype=np.uint8)
        upper = np.array([30, 170, 255], dtype=np.uint8)
        skin_mask = cv2.inRange(hsv, lower, upper)

        skin_region = gray[skin_mask > 0]
        if len(skin_region) > 100:
            # Texture uniformity: lower local std = smoother skin
            # Block-based std
            block_size = 16
            h, w = gray.shape
            local_stds = []
            for row in range(0, h - block_size, block_size):
                for col in range(0, w - block_size, block_size):
                    block = gray[row:row + block_size, col:col + block_size]
                    if np.mean(block) > 30:  # Skip dark blocks
                        local_stds.append(np.std(block))

            if local_stds:
                avg_local_std = np.mean(local_stds)
                # Lower local std = smoother, more uniform skin
                texture_score = max(0, min(100, 100 - avg_local_std * 2.5))
            else:
                texture_score = 70.0
        else:
            texture_score = 70.0

        # Blend scores
        final = brightness_score * 0.25 + contrast_score * 0.25 + texture_score * 0.5

        if final >= 80:
            desc = "Clear and radiant complexion"
        elif final >= 65:
            desc = "Healthy skin with minor unevenness"
        elif final >= 50:
            desc = "Average — skincare routine could help"
        elif final >= 35:
            desc = "Visible texture or tone issues"
        else:
            desc = "Significant skin concerns to address"

        return round(final, 1), desc

    except Exception:
        return 70.0, "Unable to assess"


# ---------------------------------------------------------------------------
# Category 3: Jawline Definition
# ---------------------------------------------------------------------------
def calculate_jawline_definition(landmarks: List[Dict]) -> Tuple[float, str]:
    """
    Calculate jawline sharpness and definition from landmark geometry.

    Returns (score 0-100, description label).
    """
    if not landmarks or len(landmarks) < 468:
        return 70.0, "Adequate definition"

    # --- Jaw width / height ratio ---
    # Chin point
    chin = landmarks[152]
    # Gonion (jaw angle) approximations
    left_gonion = landmarks[172]  # approx left jaw angle
    right_gonion = landmarks[397]  # approx right jaw angle

    jaw_width = abs(right_gonion["x"] - left_gonion["x"])
    # Height from lips to chin
    lip_center_y = landmarks[13]["y"]
    chin_y = chin["y"]
    jaw_height = abs(chin_y - lip_center_y)

    if jaw_height > 0:
        jaw_ratio = jaw_width / jaw_height
        # Ideal ratio ~2.0-2.6 for a defined jaw (wider than tall)
        ratio_score = 100 - abs(jaw_ratio - 2.3) * 40
        ratio_score = max(0, min(100, ratio_score))
    else:
        ratio_score = 70.0

    # --- Jaw angle sharpness ---
    # Check how angular the jaw corner points are
    # Use the z-depth difference around the jaw line
    jaw_points_indices = [0, 17, 61, 81, 84, 91, 146, 149, 172, 176, 178,
                          199, 207, 211, 263, 291, 308, 311, 324, 334, 365,
                          367, 376, 379, 397, 400, 409, 415]
    jaw_zs = []
    for idx in jaw_points_indices:
        if idx < len(landmarks):
            jaw_zs.append(landmarks[idx]["z"])

    if jaw_zs:
        z_range = max(jaw_zs) - min(jaw_zs)
        # More z-variance = stronger 3D definition
        angularity_score = min(100, z_range * 400)
    else:
        angularity_score = 60.0

    # --- Chin projection ---
    chin_z = chin["z"]
    lip_z = landmarks[13]["z"]
    # Chin should project slightly more than lips
    chin_projection = chin_z - lip_z  # higher = more forward chin
    projection_score = min(100, max(30, 50 + chin_projection * 300))

    final = ratio_score * 0.35 + angularity_score * 0.35 + projection_score * 0.3

    if final >= 80:
        desc = "Strong and well-defined jawline"
    elif final >= 65:
        desc = "Good structure with natural definition"
    elif final >= 50:
        desc = "Adequate — could benefit from definition exercises"
    elif final >= 35:
        desc = "Softer jaw — targeted work recommended"
    else:
        desc = "Minimal definition — focus on jaw exercises"

    return round(final, 1), desc


# ---------------------------------------------------------------------------
# Category 4: Eye Appeal
# ---------------------------------------------------------------------------
def calculate_eye_appeal(landmarks: List[Dict]) -> Tuple[float, str]:
    """
    Calculate eye symmetry, spacing, and shape appeal.

    Returns (score 0-100, description label).
    """
    if not landmarks or len(landmarks) < 468:
        return 75.0, "Pleasant eye shape"

    # --- Inter-pupillary distance (IPD) ratio ---
    # Left eye center (approx pupil)
    if all(i < len(landmarks) for i in [159, 158, 157, 173, 33, 133]):
        left_eye_cx = sum(landmarks[i]["x"] for i in [33, 133, 159, 158, 157, 173]) / 6
        left_eye_cy = sum(landmarks[i]["y"] for i in [33, 133, 159, 158, 157, 173]) / 6
    else:
        left_eye_cx, left_eye_cy = 0.35, 0.45

    if all(i < len(landmarks) for i in [386, 385, 384, 398, 362, 263]):
        right_eye_cx = sum(landmarks[i]["x"] for i in [362, 263, 386, 385, 384, 398]) / 6
        right_eye_cy = sum(landmarks[i]["y"] for i in [362, 263, 386, 385, 384, 398]) / 6
    else:
        right_eye_cx, right_eye_cy = 0.65, 0.45

    eye_separation = abs(right_eye_cx - left_eye_cx)
    # Face width
    face_width = abs(landmarks[352]["x"] - landmarks[123]["x"]) if all(i < len(landmarks) for i in [352, 123]) else 0.5

    if face_width > 0:
        eye_width_ratio = eye_separation / face_width
        # Ideal ~0.42-0.48 (eyes occupy ~45% of face width)
        separation_score = 100 - abs(eye_width_ratio - 0.45) * 250
        separation_score = max(0, min(100, separation_score))
    else:
        separation_score = 75.0

    # --- Horizontal eye alignment ---
    eye_y_diff = abs(left_eye_cy - right_eye_cy)
    alignment_score = max(0, min(100, 100 - eye_y_diff * 200))

    # --- Eye size symmetry ---
    left_width = abs(landmarks[33]["x"] - landmarks[133]["x"]) if all(i < len(landmarks) for i in [33, 133]) else 0.1
    right_width = abs(landmarks[362]["x"] - landmarks[263]["x"]) if all(i < len(landmarks) for i in [362, 263]) else 0.1

    if max(left_width, right_width) > 0:
        size_ratio = min(left_width, right_width) / max(left_width, right_width)
        size_score = size_ratio * 100
    else:
        size_score = 75.0

    # --- Eye shape (height/width ratio) ---
    left_height = abs(landmarks[159]["y"] - landmarks[145]["y"]) if all(i < len(landmarks) for i in [159, 145]) else 0.03
    left_shape_ratio = left_height / left_width if left_width > 0 else 0.3
    # Pleasant eye shape height/width ~0.25-0.35
    shape_score = 100 - abs(left_shape_ratio - 0.3) * 300
    shape_score = max(0, min(100, shape_score))

    final = separation_score * 0.25 + alignment_score * 0.25 + size_score * 0.25 + shape_score * 0.25

    if final >= 80:
        desc = "Striking and well-proportioned eyes"
    elif final >= 65:
        desc = "Pleasant eye area with good symmetry"
    elif final >= 50:
        desc = "Average eye appeal — subtle enhancements possible"
    elif final >= 35:
        desc = "Noticeable asymmetry in the eye area"
    else:
        desc = "Significant eye area concerns to address"

    return round(final, 1), desc


# ---------------------------------------------------------------------------
# Category 5: Facial Structure (cheekbones, nose, chin)
# ---------------------------------------------------------------------------
def calculate_facial_structure(landmarks: List[Dict]) -> Tuple[float, str]:
    """
    Calculate facial bone structure appeal from cheekbone width and nose ratios.

    Returns (score 0-100, description label).
    """
    if not landmarks or len(landmarks) < 468:
        return 70.0, "Balanced structure"

    # --- Cheekbone prominence (width / face width ratio) ---
    left_cheek_x = landmarks[123]["x"] if 123 < len(landmarks) else 0.38
    right_cheek_x = landmarks[352]["x"] if 352 < len(landmarks) else 0.62
    face_width = abs(right_cheek_x - left_cheek_x)

    # Jaw width
    left_jaw_x = landmarks[172]["x"] if 172 < len(landmarks) else 0.40
    right_jaw_x = landmarks[397]["x"] if 397 < len(landmarks) else 0.60
    jaw_width = abs(right_jaw_x - left_jaw_x)

    # Forehead width
    left_forehead_x = landmarks[54]["x"] if 54 < len(landmarks) else 0.37
    right_forehead_x = landmarks[284]["x"] if 284 < len(landmarks) else 0.63
    forehead_width = abs(right_forehead_x - left_forehead_x)

    # --- Cheek-to-jaw ratio ---
    # Well-defined cheeks are wider than jaw (heart/oval shape)
    if jaw_width > 0:
        cheek_jaw_ratio = face_width / jaw_width
        # Ideal cheekbones 5-10% wider than jaw
        cheek_score = 100 - max(0, (cheek_jaw_ratio - 1.07) * 300) - max(0, (0.98 - cheek_jaw_ratio) * 300)
        cheek_score = max(0, min(100, cheek_score))
    else:
        cheek_score = 70.0

    # --- Nose proportions ---
    if all(i < len(landmarks) for i in [6, 2, 64, 294]):
        # Nose length (bridge to tip)
        nose_length = abs(landmarks[2]["y"] - landmarks[6]["y"])
        # Nose width (ala to ala)
        nose_width = abs(landmarks[294]["x"] - landmarks[64]["x"])

        if nose_width > 0 and nose_length > 0:
            nose_ratio = nose_width / nose_length
            # Ideal nose width/length ~0.65-0.75
            nose_score = 100 - abs(nose_ratio - 0.7) * 200
            nose_score = max(0, min(100, nose_score))
        else:
            nose_score = 70.0
    else:
        nose_score = 70.0

    # --- Chin-to-face ratio ---
    chin_y = landmarks[152]["y"] if 152 < len(landmarks) else 0.85
    lip_y = landmarks[13]["y"] if 13 < len(landmarks) else 0.75
    nose_y = landmarks[2]["y"] if 2 < len(landmarks) else 0.60

    lower_face = abs(chin_y - nose_y) if chin_y != nose_y else 0.25
    chin_to_lip = abs(chin_y - lip_y) if chin_y != lip_y else 0.10

    if lower_face > 0:
        chin_ratio = chin_to_lip / lower_face
        # Lower third should have chin ~50-65% below lips
        chin_proportion_score = 100 - abs(chin_ratio - 0.58) * 250
        chin_proportion_score = max(0, min(100, chin_proportion_score))
    else:
        chin_proportion_score = 70.0

    final = cheek_score * 0.40 + nose_score * 0.30 + chin_proportion_score * 0.30

    if final >= 80:
        desc = "Excellent bone structure and proportions"
    elif final >= 65:
        desc = "Well-structured with pleasing ratios"
    elif final >= 50:
        desc = "Balanced structure with room for refinement"
    elif final >= 35:
        desc = "Some structural imbalance — grooming can help"
    else:
        desc = "Underdeveloped structure — consider contouring techniques"

    return round(final, 1), desc


# ---------------------------------------------------------------------------
# Category 6: Masculinity / Femininity
# ---------------------------------------------------------------------------
def calculate_masculinity_femininity(landmarks: List[Dict], gender: str) -> Tuple[float, str]:
    """
    Calculate gender-specific appeal from facial ratios.

    For males: wider jaw, prominent brow ridge, stronger chin projection.
    For females: softer jaw, higher cheekbones, smaller nose-to-face ratio.

    Returns (score 0-100, description label).
    """
    gender = gender.lower().strip() if gender else "male"
    if gender not in ("male", "female"):
        gender = "male"

    if not landmarks or len(landmarks) < 468:
        return 70.0, "Balanced features"

    # --- Jaw-to-cheek ratio ---
    jaw_left = landmarks[172]["x"] if 172 < len(landmarks) else 0.40
    jaw_right = landmarks[397]["x"] if 397 < len(landmarks) else 0.60
    cheek_left = landmarks[123]["x"] if 123 < len(landmarks) else 0.38
    cheek_right = landmarks[352]["x"] if 352 < len(landmarks) else 0.62
    jaw_width = abs(jaw_right - jaw_left)
    cheek_width = abs(cheek_right - cheek_left)

    if cheek_width > 0:
        jaw_cheek_ratio = jaw_width / cheek_width
    else:
        jaw_cheek_ratio = 1.0

    # --- Brow ridge prominence (z-depth) ---
    brow_zs = []
    for idx in LEFT_BROW + RIGHT_BROW:
        if idx < len(landmarks):
            brow_zs.append(landmarks[idx]["z"])
    avg_brow_z = np.mean(brow_zs) if brow_zs else 0.0

    # Eye region z-depth for comparison
    eye_zs = []
    for idx in LEFT_EYE + RIGHT_EYE:
        if idx < len(landmarks):
            eye_zs.append(landmarks[idx]["z"])
    avg_eye_z = np.mean(eye_zs) if eye_zs else 0.0

    brow_prominence = avg_brow_z - avg_eye_z  # positive = more prominent brow

    # --- Chin projection ---
    chin_z = landmarks[152]["z"] if 152 < len(landmarks) else 0.02
    lip_z = landmarks[13]["z"] if 13 < len(landmarks) else 0.0
    chin_projection = chin_z - lip_z

    if gender == "male":
        # Wider jaw relative to cheeks (more square/angular): ideal ratio ~0.92-0.98
        jaw_score = 100 - abs(jaw_cheek_ratio - 0.95) * 300
        jaw_score = max(0, min(100, jaw_score))

        # More prominent brow ridge is masculine
        brow_score = min(100, max(30, 50 + brow_prominence * 400))

        # Stronger chin projection
        chin_score = min(100, max(30, 50 + chin_projection * 400))

        desc_suffix = "Strong masculine features"
    else:
        # Narrower jaw relative to cheeks (softer, heart/oval): ideal ratio ~0.85-0.92
        jaw_score = 100 - abs(jaw_cheek_ratio - 0.88) * 300
        jaw_score = max(0, min(100, jaw_score))

        # Less prominent brow (more open eye area) is feminine
        brow_score = 100 - min(70, abs(brow_prominence) * 300)

        # Moderate chin projection
        chin_score = 100 - min(70, abs(chin_projection - 0.005) * 300)

        desc_suffix = "Soft feminine proportions"

    final = jaw_score * 0.40 + brow_score * 0.30 + chin_score * 0.30

    if final >= 80:
        desc = f"Excellent — {desc_suffix}"
    elif final >= 65:
        desc = f"Good — {desc_suffix}"
    elif final >= 50:
        desc = f"Balanced features with room for enhancement"
    elif final >= 35:
        desc = "Some features could be refined for your goals"
    else:
        desc = "Features may benefit from targeted enhancement"

    return round(final, 1), desc


# ---------------------------------------------------------------------------
# Heuristic fallback (when no landmarks available)
# ---------------------------------------------------------------------------
def _heuristic_breakdown(
    overall_score: float,
    image_bytes: Optional[bytes] = None,
    gender: str = "male",
) -> Dict[str, Any]:
    """
    Generate a category breakdown using heuristic estimates when landmarks aren't available.
    Uses the overall score as a baseline, adjusted by image quality.
    """
    # Get skin quality from image (this doesn't need landmarks)
    skin_score, skin_desc = calculate_skin_quality(image_bytes) if image_bytes else (70.0, "Unable to assess")

    # Use overall score as baseline, add small random-ish variation
    base = overall_score

    # Derive other scores from the base with category-appropriate offsets
    harmony = min(100, max(20, base + 3))
    jawline = min(100, max(20, base - 2 if gender == "male" else base - 5))
    eyes = min(100, max(20, base + 1))
    structure = min(100, max(20, base))
    mascfem = min(100, max(20, base + (4 if gender == "male" else -2)))

    def describe(score, category_name):
        if score >= 80:
            return f"Excellent {category_name.lower()}"
        elif score >= 65:
            return f"Good {category_name.lower()}"
        elif score >= 50:
            return f"Adequate {category_name.lower()}"
        elif score >= 35:
            return f"{category_name} needs attention"
        else:
            return f"{category_name} requires focus"

    return {
        "facial_harmony": {"score": round(harmony, 1), "description": describe(harmony, "Facial Harmony")},
        "skin_quality": {"score": round(skin_score, 1), "description": skin_desc},
        "jawline_definition": {"score": round(jawline, 1), "description": describe(jawline, "Jawline Definition")},
        "eye_appeal": {"score": round(eyes, 1), "description": describe(eyes, "Eye Appeal")},
        "facial_structure": {"score": round(structure, 1), "description": describe(structure, "Facial Structure")},
        "masculinity_femininity": {"score": round(mascfem, 1), "description": describe(mascfem, "Gender Appeal")},
        "heuristic": True,
    }


# ---------------------------------------------------------------------------
# Main entry point: get all category scores
# ---------------------------------------------------------------------------
def get_category_breakdown(
    image_bytes: bytes,
    landmarks: Optional[List[Dict]] = None,
    gender: str = "male",
    overall_score: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Calculate all 6 category scores and descriptions.

    Args:
        image_bytes: Raw image bytes (needed for skin quality analysis).
        landmarks: Optional list of 468 landmarks from MediaPipe. If None or
                   empty, heuristic fallback is used.
        gender: "male" or "female".
        overall_score: Pre-calculated overall score (used for fallback heuristics).

    Returns:
        dict with keys for each category, each containing score (float) and
        description (str). Also includes an "heuristic" flag if fallback was used.
    """
    if not landmarks or len(landmarks) < 100:
        # No useful landmarks — use heuristics
        return _heuristic_breakdown(
            overall_score=overall_score or 70.0,
            image_bytes=image_bytes,
            gender=gender,
        )

    # Calculate all 6 categories
    harmony_score, harmony_desc = calculate_facial_harmony(landmarks)
    skin_score, skin_desc = calculate_skin_quality(image_bytes)
    jawline_score, jawline_desc = calculate_jawline_definition(landmarks)
    eye_score, eye_desc = calculate_eye_appeal(landmarks)
    structure_score, structure_desc = calculate_facial_structure(landmarks)
    mascfem_score, mascfem_desc = calculate_masculinity_femininity(landmarks, gender)

    return {
        "facial_harmony": {"score": harmony_score, "description": harmony_desc},
        "skin_quality": {"score": skin_score, "description": skin_desc},
        "jawline_definition": {"score": jawline_score, "description": jawline_desc},
        "eye_appeal": {"score": eye_score, "description": eye_desc},
        "facial_structure": {"score": structure_score, "description": structure_desc},
        "masculinity_femininity": {"score": mascfem_score, "description": mascfem_desc},
        "heuristic": False,
    }