"""
Background ML analysis service.

Runs MediaPipe face analysis and ML prediction in a background task
so that the upload endpoint can return immediately (~1.5 s instead of ~8.8 s).

The photo is saved with analysis_status="processing", then this function
updates it to "completed" or "failed" when done.
"""
from app.database import SessionLocal
from app.models import Photo, Plan
from app.services.prediction_service import prediction_service
from app.services.face_service import (
    detect_face_landmarks,
    calculate_symmetry,
    calculate_skin_score,
    calculate_jawline_score,
    calculate_eye_score,
    generate_overall_score,
    get_face_shape,
)
from app.services.face_analysis_service import get_category_breakdown
from app.services.ai_service import generate_fallback_analysis
from app.services.plan_generator_service import generate_fallback_plan
from app.services.score_labels import get_score_label
from app.services.validation_service import validate_image
import uuid
import asyncio
import logging
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


def run_analysis_background(photo_id: str, user_id: str, image_bytes: bytes, gender: str = "male"):
    """
    Run ML prediction, face analysis, and scoring in the background.

    1. Runs prediction_service.predict() for the holistic score
    2. Runs face landmark detection + per-category scoring
    3. Generates template-based analysis + 90-day plan
    4. Updates the photo record with full results
    5. Sets analysis_status to "completed" or "failed"
    """
    db_bg = SessionLocal()
    try:
        # ── Mark as processing ───────────────────────────────────
        photo = db_bg.query(Photo).filter(Photo.id == photo_id, Photo.user_id == user_id).first()
        if not photo:
            logger.error(f"Background analysis: photo {photo_id} not found")
            return
        photo.analysis_status = "processing"
        db_bg.commit()

        # ── 0. Pre-validation: reject unusable images before any AI work ──
        validation = validate_image(image_bytes)
        if not validation.get("valid"):
            photo.analysis_status = "failed"
            photo.analysis_details = {
                "validation_error": validation.get("error"),
                "valid": False,
            }
            db_bg.commit()
            logger.info(f"❌ Photo {photo_id} rejected in pre-validation: {validation.get('error')}")
            return

        # ── 1. ML prediction (holistic score) ─────────────────────
        score = None
        try:
            prediction = prediction_service.predict(image_bytes, gender=gender)
            score = prediction.get("score_100", None)
        except Exception as exc:
            logger.warning(f"Background prediction failed for {photo_id}: {exc}")

        # ── 2. Face landmark detection + per-category scoring ─────
        overall_score = score or 50.0
        symmetry_score = None
        skin_score = None
        jawline_score = None
        eye_score = None
        face_shape = None
        category_breakdown = {}
        analysis_data = {}
        plan_data = {}

        landmarks = None
        try:
            face_result = detect_face_landmarks(image_bytes)
            if face_result.get("success"):
                landmarks = face_result.get("landmarks") or []
            else:
                logger.warning(
                    f"Face landmark detection failed for {photo_id}: "
                    f"{face_result.get('error')} — using heuristic category breakdown"
                )
        except Exception as exc:
            logger.warning(f"Background face detection failed for {photo_id}: {exc}")

        if landmarks and len(landmarks) >= 100:
            symmetry_score = calculate_symmetry(landmarks)
            skin_score = calculate_skin_score(landmarks, image_bytes)
            jawline_score = calculate_jawline_score(landmarks)
            eye_score = calculate_eye_score(landmarks)
            face_shape = get_face_shape(landmarks)

            scores = {
                "symmetry": symmetry_score,
                "skin": skin_score,
                "jawline": jawline_score,
                "eyes": eye_score,
                "nose": 70.0,
                "lips": 75.0,
            }
            overall_score = generate_overall_score(scores)

        # Always produce a category breakdown — never leave it empty.
        try:
            category_breakdown = get_category_breakdown(
                image_bytes=image_bytes,
                landmarks=landmarks if landmarks and len(landmarks) >= 100 else None,
                gender=gender,
                overall_score=overall_score,
            )
        except Exception as exc:
            logger.warning(f"Category breakdown failed for {photo_id}: {exc}")
            category_breakdown = {
                "facial_harmony": {"score": round(overall_score, 1), "description": "Estimate based on overall score"},
                "skin_quality": {"score": round(overall_score, 1), "description": "Estimate based on overall score"},
                "jawline_definition": {"score": round(overall_score, 1), "description": "Estimate based on overall score"},
                "eye_appeal": {"score": round(overall_score, 1), "description": "Estimate based on overall score"},
                "facial_structure": {"score": round(overall_score, 1), "description": "Estimate based on overall score"},
                "masculinity_femininity": {"score": round(overall_score, 1), "description": "Estimate based on overall score"},
                "heuristic": True,
            }

        # ── 3. Template-based analysis + plan ────────────────────
        score_data = {
            "overall_score": overall_score,
            "symmetry_score": symmetry_score,
            "skin_score": skin_score,
            "jawline_score": jawline_score,
            "eye_score": eye_score,
            "face_shape": face_shape,
        }
        try:
            fallback_analysis = generate_fallback_analysis(score_data)
            analysis_data = fallback_analysis.get("data", {})
        except Exception as exc:
            logger.warning(f"Background template analysis failed for {photo_id}: {exc}")

        try:
            plan_data = generate_fallback_plan(overall_score, gender=gender)
        except Exception as exc:
            logger.warning(f"Background plan generation failed for {photo_id}: {exc}")

        # ── 4. Convert NumPy to native Python ────────────────────
        def _py(val):
            if val is None:
                return None
            if isinstance(val, (np.integer, np.floating)):
                return val.item()
            if isinstance(val, np.ndarray):
                return val.tolist()
            return val

        def _json_safe(obj):
            if isinstance(obj, dict):
                return {k: _json_safe(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_json_safe(item) for item in obj]
            if isinstance(obj, (np.integer, np.floating)):
                return obj.item()
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj

        # ── 5. Update photo record ───────────────────────────────
        if score is not None:
            photo.score = _py(score)
        photo.symmetry_score = _py(symmetry_score)
        photo.skin_score = _py(skin_score)
        photo.jawline_score = _py(jawline_score)
        photo.eye_score = _py(eye_score)
        photo.face_shape = face_shape
        photo.strengths = analysis_data.get("strengths", [])
        photo.weaknesses = analysis_data.get("weaknesses", [])
        photo.analysis_details = _json_safe({
            "category_breakdown": category_breakdown,
            "deepseek_analysis": {},
            "source": "template",
        })
        photo.analysis_status = "completed"

        # ── 6. Create or update plan ─────────────────────────────
        if plan_data:
            existing_plan = (
                db_bg.query(Plan)
                .filter(Plan.photo_id == photo_id, Plan.user_id == user_id)
                .first()
            )
            if existing_plan:
                existing_plan.data = plan_data
                existing_plan.updated_at = datetime.utcnow()
                existing_plan.is_active = True
            else:
                # Plans are per-photo. Deactivate any older plans so only the
                # latest photo's plan is active (GET /plan then returns it instantly).
                db_bg.query(Plan).filter(
                    Plan.user_id == user_id, Plan.is_active == True
                ).update({Plan.is_active: False}, synchronize_session=False)

                new_plan = Plan(
                    id=str(uuid.uuid4()),
                    photo_id=photo_id,
                    user_id=user_id,
                    data=plan_data,
                    phases=plan_data.get("phases", {}),
                    current_phase="week_1",
                    current_week=1,
                    is_active=True,
                )
                db_bg.add(new_plan)

        db_bg.commit()
        logger.info(f"✅ Background analysis completed for photo {photo_id} (score={score})")

    except Exception as exc:
        db_bg.rollback()
        logger.error(f"❌ Background analysis failed for photo {photo_id}: {exc}")
        # Try to mark as failed
        try:
            photo = db_bg.query(Photo).filter(Photo.id == photo_id).first()
            if photo:
                photo.analysis_status = "failed"
                db_bg.commit()
        except Exception:
            pass
    finally:
        db_bg.close()


async def run_analysis_in_background(
    photo_id: str, user_id: str, image_bytes: bytes, gender: str = "male"
):
    """Run the blocking ML analysis in a thread pool so it never blocks the event loop.

    `run_analysis_background` does CPU-bound work (torch inference, MediaPipe,
    PIL) that would otherwise stall every other request (status polling, plan
    fetch) in the single-worker event loop. Offloading it to an executor keeps
    the API responsive while analysis runs.
    """
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, run_analysis_background, photo_id, user_id, image_bytes, gender
    )