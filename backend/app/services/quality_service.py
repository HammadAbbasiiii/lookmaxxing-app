"""
Image quality checks for the prediction pipeline.
Replicates the quality checks from Kaggle notebook:
  - Brightness check
  - Blur detection
  - Face size validation
"""
import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional


def check_image_brightness(img: np.ndarray) -> Dict[str, object]:
    """
    Check if the image is too dark or too bright.
    Returns a dict with brightness value (0–255) and a warning if applicable.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    brightness = float(np.mean(gray))

    warnings: List[str] = []
    if brightness < 40:
        warnings.append("Image is too dark. Use better lighting for accurate results.")
    elif brightness < 60:
        warnings.append("Image is slightly dark. Brighter lighting may improve accuracy.")
    elif brightness > 230:
        warnings.append("Image is too bright/overexposed. Avoid direct sunlight.")

    return {"brightness": round(brightness, 1), "warnings": warnings}


def check_image_blur(img: np.ndarray) -> Dict[str, object]:
    """
    Check if the image is blurry using Laplacian variance.
    Returns a dict with blur score and a warning if applicable.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    warnings: List[str] = []
    if blur_score < 50:
        warnings.append("Image is blurry. Hold the camera steady for sharper results.")
    elif blur_score < 100:
        warnings.append("Image is slightly blurry. Try to reduce motion blur.")

    return {"blur_score": round(blur_score, 1), "warnings": warnings}


def check_face_size(
    face_location: Tuple[int, int, int, int], img_shape: Tuple[int, int, int]
) -> Dict[str, object]:
    """
    Check if the detected face occupies enough of the image.
    face_location: (top, right, bottom, left) in pixels.
    img_shape: (height, width, channels).
    """
    top, right, bottom, left = face_location
    h, w = img_shape[:2]
    face_h = bottom - top
    face_w = right - left
    face_area = face_h * face_w
    img_area = h * w
    face_ratio = face_area / img_area if img_area > 0 else 0.0

    warnings: List[str] = []
    if face_ratio < 0.05:
        warnings.append("Face is too small in the image. Move closer for better results.")
    elif face_ratio < 0.10:
        warnings.append("Face could be larger. Step a bit closer to the camera.")

    return {"face_ratio": round(face_ratio, 4), "warnings": warnings}


def run_quality_checks(
    img: np.ndarray,
    face_location: Optional[Tuple[int, int, int, int]] = None
) -> Dict[str, object]:
    """
    Run all quality checks on an image and aggregate warnings.
    Returns a dict with all check results and combined warnings list.
    """
    all_warnings: List[str] = []
    results: Dict[str, object] = {}

    # Brightness check
    brightness_result = check_image_brightness(img)
    results["brightness"] = brightness_result
    all_warnings.extend(
        w for w in brightness_result.get("warnings", [])  # type: ignore
    )

    # Blur check
    blur_result = check_image_blur(img)
    results["blur"] = blur_result
    all_warnings.extend(
        w for w in blur_result.get("warnings", [])  # type: ignore
    )

    # Face size check
    if face_location is not None:
        size_result = check_face_size(face_location, img.shape)
        results["face_size"] = size_result
        all_warnings.extend(
            w for w in size_result.get("warnings", [])  # type: ignore
        )

    results["warnings"] = all_warnings
    results["passed"] = len(all_warnings) == 0

    return results