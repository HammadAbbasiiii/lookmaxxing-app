"""
Kaggle RankInfoNet Prediction Service.
Loads the trained model at startup and runs inference on user photos.

Architecture:
  - Lazy imports for PyTorch — app starts even without torch installed
  - Module-level singleton loaded once at startup
  - Graceful fallback to mock predictions when model/PyTorch unavailable
  - Integrates quality checks, face detection, model inference,
    score labeling, and category breakdown in one pipeline.
"""
import io
import time
import logging

import numpy as np
from PIL import Image, ImageEnhance, ImageOps

from app.services.quality_service import run_quality_checks
from app.services.score_labels import get_score_label

logger = logging.getLogger(__name__)

# ── Lazy PyTorch imports ─────────────────────────────────────────────────
_torch = None
_torch_nn = None
_torch_transform = None
_RankInfoNet = None
_TORCH_AVAILABLE = None  # None = not yet checked, False = not available, True = available
_TORCH_IMPORT_ERROR = None

_torchvision_transform = None


def _ensure_torch() -> bool:
    """Lazily attempt to import torch and RankInfoNet. Returns True on success."""
    global _torch, _torch_nn, _torch_transform, _RankInfoNet, _TORCH_AVAILABLE, _TORCH_IMPORT_ERROR, _torchvision_transform
    if _TORCH_AVAILABLE is not None:
        return _TORCH_AVAILABLE
    try:
        import torch as _t
        import torch.nn as _tn
        from torchvision import transforms as _tvtransforms
        from app.ml.ml_model import RankInfoNet as _rin
        _torch = _t
        _torch_nn = _tn
        _torchvision_transform = _tvtransforms
        _RankInfoNet = _rin
        _TORCH_AVAILABLE = True
        logger.info("✅ PyTorch and RankInfoNet imported successfully")
        return True
    except Exception as exc:
        _TORCH_IMPORT_ERROR = str(exc)
        _TORCH_AVAILABLE = False
        logger.warning(f"⚠️ PyTorch/RankInfoNet not available, using mock predictions: {exc}")
        return False


# Image transform (created lazily when torch is available)
def _get_transform():
    if _torchvision_transform is not None:
        return _torchvision_transform.Compose([
            _torchvision_transform.Resize((224, 224)),
            _torchvision_transform.ToTensor(),
            _torchvision_transform.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    return None


# ── PredictionService — Singleton ───────────────────────────────────────
class PredictionService:
    """Loads RankInfoNet once and reuses for all predictions."""

    def __init__(self) -> None:
        self.model: object | None = None
        self.device = None
        self.model_loaded: bool = False

    # ── Model loading (called from main.py startup) ──────────────────────
    def load_model(self, model_path: str | None = None) -> bool:
        """Load the trained RankInfoNet model. Returns True on success."""
        from app.config import settings
        path = model_path or settings.MODEL_PATH

        if not _ensure_torch():
            logger.warning("PyTorch unavailable — skipping model load")
            self.model = None
            self.model_loaded = False
            return False

        try:
            self.device = _torch.device("cuda" if _torch.cuda.is_available() else "cpu")

            # Model was trained in a Jupyter notebook where RankInfoNet
            # lives in __main__ — patch __main__ so unpickling works.
            import __main__
            __main__.RankInfoNet = _RankInfoNet

            checkpoint = _torch.load(path, map_location=self.device, weights_only=False)

            # The file may contain the full model or just state_dict
            if isinstance(checkpoint, dict):
                model = _RankInfoNet()
                model.load_state_dict(checkpoint)
            else:
                model = checkpoint

            model.to(self.device)
            model.eval()
            self.model = model
            self.model_loaded = True
            logger.info(f"✅ RankInfoNet model loaded on {self.device} from {path}")
            return True
        except FileNotFoundError:
            logger.warning(f"❌ Model file not found at {path}. Using mock predictions.")
            self.model = None
            self.model_loaded = False
            return False
        except Exception as exc:
            logger.warning(f"❌ Failed to load model: {exc}. Using mock predictions.")
            self.model = None
            self.model_loaded = False
            return False

    # ── Main prediction entry point ────────────────────────────────────
    def predict(self, image_bytes: bytes, gender: str | None = None) -> dict:
        """
        Run the full prediction pipeline on raw image bytes.

        Returns dict with keys: score, score_100, label, emoji, message,
        categories, warnings, processing_time_ms, model_used
        """
        t0 = time.time()

        # Decode image
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as exc:
            return {
                "error": f"Failed to decode image: {exc}",
                "score": 0.0,
                "score_100": 0.0,
                "label": "Unknown",
                "emoji": "❓",
                "message": "Could not process this image.",
                "categories": {},
                "warnings": ["Image could not be decoded."],
                "processing_time_ms": 0.0,
                "model_used": False,
            }

        # Quality checks
        cv_img = np.array(img)
        quality = run_quality_checks(cv_img)
        warnings: list = quality.get("warnings", [])

        # Face detection
        from app.services.face_analysis_service import extract_face_landmarks
        face_result = extract_face_landmarks(image_bytes)
        if not face_result.get("success"):
            warnings.append(face_result.get("error", "No face detected"))
            face_loc = None
        else:
            landmarks = face_result.get("landmarks", [])
            face_loc = self._landmarks_to_bbox(landmarks, img.size) if landmarks else None

        # Model inference or mock
        if self.model is not None and face_loc is not None:
            try:
                processed = self._preprocess_image(img, face_loc)
                transform_fn = _get_transform()
                if transform_fn is None:
                    raise RuntimeError("Torch transforms not available")
                tensor = transform_fn(processed).unsqueeze(0).to(self.device)

                with _torch.no_grad():
                    score = float(self.model(tensor).item())

                score_100 = self._raw_to_100(score)
                model_used = True
            except Exception as exc:
                logger.warning(f"Model inference failed, falling back to mock: {exc}")
                score, score_100 = self._mock_score()
                model_used = False
        else:
            score, score_100 = self._mock_score()
            model_used = False

        # Score labeling
        tier = get_score_label(score_100)

        # Category breakdown
        try:
            from app.services.face_analysis_service import get_category_breakdown
            categories = get_category_breakdown(
                image_bytes=image_bytes,
                landmarks=face_result.get("landmarks"),
                gender=gender or "male",
                overall_score=score_100,
            )
        except Exception:
            categories = {
                "jawline": {"score": 50, "label": "Average"},
                "eyes": {"score": 50, "label": "Average"},
                "skin": {"score": 50, "label": "Average"},
                "symmetry": {"score": 50, "label": "Average"},
                "structure": {"score": 50, "label": "Average"},
                "appeal": {"score": 50, "label": "Average"},
            }

        # Gender-specific labels
        try:
            from app.services.score_labels import get_gender_specific_labels
            if gender in ("male", "female"):
                gt = get_gender_specific_labels(gender, score_100)
                if gt and gt.get("label"):
                    tier = gt
        except Exception:
            pass

        processing_time_ms = round((time.time() - t0) * 1000, 2)

        return {
            "score": round(score, 5),
            "score_100": round(score_100, 1),
            "label": tier.get("label", "Average"),
            "emoji": tier.get("emoji", "😐"),
            "message": tier.get("description", ""),
            "categories": categories,
            "warnings": warnings,
            "processing_time_ms": processing_time_ms,
            "model_used": model_used,
        }

    # ── Helpers ──────────────────────────────────────────────────────
    @staticmethod
    def _raw_to_100(raw_score: float) -> float:
        """Convert model output (1–5 range) to 0–100 scale."""
        return (raw_score - 1.0) / 4.0 * 100.0

    @staticmethod
    def _mock_score() -> tuple:
        """Generate a plausible mock score when model is unavailable."""
        import random
        raw = 1.0 + random.random() * 4.0
        score_100 = (raw - 1.0) / 4.0 * 100.0
        return raw, score_100

    @staticmethod
    def _landmarks_to_bbox(landmarks: list, img_size: tuple) -> tuple | None:
        """Convert landmarks to bounding box in pixel coords."""
        if not landmarks:
            return None
        w, h = img_size
        xs = [lm.get("x", 0) for lm in landmarks if lm.get("x", 0) is not None]
        ys = [lm.get("y", 0) for lm in landmarks if lm.get("y", 0) is not None]
        if not xs or not ys:
            return None

        max_x, min_x = max(xs), min(xs)
        max_y, min_y = max(ys), min(ys)

        if max_x <= 1.0 and max_y <= 1.0:
            left, right = int(min_x * w), int(max_x * w)
            top, bottom = int(min_y * h), int(max_y * h)
        else:
            left, right = int(min_x), int(max_x)
            top, bottom = int(min_y), int(max_y)

        left = max(0, min(left, w))
        right = max(0, min(right, w))
        top = max(0, min(top, h))
        bottom = max(0, min(bottom, h))

        if right <= left or bottom <= top:
            return None
        return (top, right, bottom, left)

    @staticmethod
    def _preprocess_image(img: Image.Image, face_location: tuple | None) -> Image.Image:
        """Crop face with padding, resize, sharpen, enhance contrast."""
        if face_location:
            top, right, bottom, left = face_location
            pad = 30
            w, h = img.size
            top = max(0, top - pad)
            right = min(w, right + pad)
            bottom = min(h, bottom + pad)
            left = max(0, left - pad)
            if right > left and bottom > top:
                img = img.crop((left, top, right, bottom))

        img = img.resize((224, 224), Image.Resampling.LANCZOS)

        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.8)

        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.3)

        return img


# ── Module-level singleton ────────────────────────────────────────────────
prediction_service = PredictionService()