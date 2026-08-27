from fastapi import APIRouter, HTTPException, status, Depends, File, UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Photo, Plan
from app.schemas import PhotoUploadResponse, PhotoStatusResponse, APIResponse
from app.dependencies import get_current_user
from app.services.upload_service import upload_to_cloudinary, delete_from_cloudinary
from app.services.face_service import (
    detect_face_landmarks,
    calculate_symmetry,
    calculate_skin_score,
    calculate_jawline_score,
    calculate_eye_score,
    generate_overall_score,
    get_face_shape
)
from app.services.face_analysis_service import get_category_breakdown
from app.services.ai_service import analyze_face_with_deepseek, generate_fallback_analysis
from app.services.plan_generator_service import generate_action_plan, generate_fallback_plan
from app.services.score_labels import get_score_label
from app.services.prediction_service import prediction_service
from app.services.background_analysis import run_analysis_in_background
from app.config import settings
import uuid
from datetime import datetime
import time
import logging
import json
import numpy as np

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photos", tags=["Photos"])

@router.post("/upload", response_model=PhotoUploadResponse)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Upload a photo for analysis.  Analysis runs in the background;
    the response returns immediately (~1.5 s instead of ~8.8 s).

    - Supported formats: JPG, PNG, HEIC
    - Max size: 10MB
    - Returns photo ID and URL with analysis_status="processing"
    """
    # ⏱️ Start timing
    timings = {}
    start_total = time.perf_counter()

    # Validate file type
    allowed_extensions = [".jpg", ".jpeg", ".png", ".heic"]
    file_ext = f".{file.filename.split('.')[-1].lower()}"
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
        )

    # 1. ⏱️ Time to read file from client
    read_start = time.perf_counter()
    file_size = 0
    file_content = b""
    chunk_size = 1024 * 1024  # 1MB chunks
    while chunk := await file.read(chunk_size):
        file_size += len(chunk)
        file_content += chunk
        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB"
            )
    timings["read_from_client_ms"] = round((time.perf_counter() - read_start) * 1000, 2)

    # 📄 Log file size
    file_size_kb = len(file_content) / 1024
    print(f"📄 File received: {file_size_kb:.2f} KB ({file.filename})")

    # 2. ⏱️ Time to upload to Cloudinary
    cloudinary_start = time.perf_counter()
    try:
        file_url = upload_to_cloudinary(file_content, file.filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )
    timings["cloudinary_upload_ms"] = round((time.perf_counter() - cloudinary_start) * 1000, 2)

    # Check if this is the user's first photo (baseline)
    existing_photos = db.query(Photo).filter(Photo.user_id == current_user.id).count()
    is_baseline = existing_photos == 0

    # Determine week_number from the active plan progress
    plan = (
        db.query(Plan)
        .filter(Plan.user_id == current_user.id, Plan.is_active == True)
        .order_by(Plan.created_at.desc())
        .first()
    )
    week_number = plan.current_week if (plan and plan.current_week) else 1

    # ── Save photo record (analysis_status will default to "pending") ──
    new_photo = Photo(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        file_url=file_url,
        file_size=file_size,
        file_type=file_ext,
        is_baseline=is_baseline,
        week_number=week_number,
        analysis_status="processing",  # will be set to "completed"/"failed" by background task
    )

    # 3. ⏱️ Time for database write (only the INSERT — ML is now background)
    db_start = time.perf_counter()
    db.add(new_photo)
    db.commit()
    db.refresh(new_photo)
    timings["database_save_ms"] = round((time.perf_counter() - db_start) * 1000, 2)

    # 4. ⏱️ Total time (no ML inline timing needed)
    timings["total_ms"] = round((time.perf_counter() - start_total) * 1000, 2)
    print(f"⏱️ Upload timings (analysis queued): {timings}")

    # ── Fire background analysis in a thread pool (7-8 s ML work) ──
    # run_analysis_background is CPU-bound (torch/MediaPipe/PIL). Running it via
    # run_in_executor keeps it off the event loop so status polling and other
    # requests stay responsive while analysis runs.
    gender = getattr(current_user, "gender", None) or "male"
    if background_tasks:
        background_tasks.add_task(
            run_analysis_in_background,
            photo_id=new_photo.id,
            user_id=current_user.id,
            image_bytes=file_content,
            gender=gender,
        )
    else:
        # Fallback: run in a thread pool inline if background tasks are
        # unavailable (e.g., testing).
        logger.warning("BackgroundTasks not available — running analysis in thread pool")
        await run_analysis_in_background(
            photo_id=new_photo.id,
            user_id=current_user.id,
            image_bytes=file_content,
            gender=gender,
        )

    return {
        "id": new_photo.id,
        "user_id": new_photo.user_id,
        "file_url": new_photo.file_url,
        "score": None,  # not yet available
        "is_baseline": new_photo.is_baseline,
        "week_number": new_photo.week_number,
        "captured_at": new_photo.captured_at,
        "analysis_status": new_photo.analysis_status,
        "debug_timings": timings,
    }

@router.get("/all", response_model=list[PhotoUploadResponse])
async def get_all_photos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all photos for the current user.
    """
    photos = db.query(Photo).filter(Photo.user_id == current_user.id).order_by(Photo.captured_at.desc()).all()
    return photos

@router.delete("/{photo_id}")
async def delete_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a photo.
    """
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.user_id == current_user.id).first()
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )
    
    # Delete from Cloudinary
    try:
        # Extract public_id from URL (Cloudinary stores it)
        public_id = photo.file_url.split("/")[-1].split(".")[0]
        # Need to add folder prefix
        full_public_id = f"lookmaxx/photos/user_{public_id}"
        delete_from_cloudinary(full_public_id)
    except Exception:
        pass  # Continue even if Cloudinary delete fails
    
    db.delete(photo)
    db.commit()
    
    return {"message": "Photo deleted successfully"}


@router.get("/{photo_id}/status", response_model=PhotoStatusResponse)
async def get_analysis_status(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Poll the analysis status of a photo.

    Returns:
    - analysis_status: "pending" | "processing" | "completed" | "failed"
    - score: the overall score (None if not yet computed)
    - category_breakdown, strengths, weaknesses: available once completed
    """
    photo = db.query(Photo).filter(
        Photo.id == photo_id, Photo.user_id == current_user.id
    ).first()
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )

    category_breakdown = None
    validation_error = None
    if photo.analysis_details:
        category_breakdown = photo.analysis_details.get("category_breakdown")
        validation_error = photo.analysis_details.get("validation_error")

    return {
        "id": photo.id,
        "analysis_status": photo.analysis_status or "pending",
        "score": photo.score,
        "category_breakdown": category_breakdown,
        "strengths": photo.strengths,
        "weaknesses": photo.weaknesses,
        "error": validation_error,
        "message": validation_error,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Background enrichment task — runs AFTER response is sent to the user
# ═══════════════════════════════════════════════════════════════════════════════
def _enrich_with_deepseek_background(
    photo_id: str,
    user_id: str,
    score_data: dict,
    category_breakdown: dict,
    fallback_analysis: dict,
    fallback_plan: dict,
):
    """
    Run DeepSeek calls in the background after the response has been sent.
    On success, updates the photo and plan records in the database.
    On failure, the existing template data remains as-is.
    """
    from app.database import SessionLocal
    db_bg = SessionLocal()
    try:
        # --- Call 1: DeepSeek face analysis (with 15s timeout) ---
        deepseek_result = analyze_face_with_deepseek(score_data, "")
        deepseek_data = deepseek_result.get("data", {}) if deepseek_result.get("success") else {}

        if not deepseek_result.get("success"):
            # DeepSeek call failed or timed out — keep fallback data
            logger.info(f"Background DeepSeek analysis skipped for photo {photo_id} — keeping template")
            return

        # --- Call 2: Generate DeepSeek-personalised plan ---
        enriched_plan = generate_action_plan(
            score_data=score_data,
            category_breakdown=category_breakdown,
            user_profile={"gender": "male"},
        )

        # --- Update photo record with DeepSeek-enriched data ---
        photo = db_bg.query(Photo).filter(Photo.id == photo_id, Photo.user_id == user_id).first()
        if photo:
            photo.strengths = deepseek_data.get("strengths", fallback_analysis["data"].get("strengths", []))
            photo.weaknesses = deepseek_data.get("weaknesses", fallback_analysis["data"].get("weaknesses", []))
            if photo.analysis_details is None:
                photo.analysis_details = {}
            photo.analysis_details["deepseek_analysis"] = deepseek_data

        # --- Update or create the plan with enriched data ---
        existing_plan = db_bg.query(Plan).filter(Plan.photo_id == photo_id).first()
        if existing_plan:
            existing_plan.data = enriched_plan
            existing_plan.updated_at = datetime.utcnow()
            existing_plan.is_active = True
        else:
            # One active plan per user — deactivate older plans so GET /plan
            # returns this photo's plan instantly.
            db_bg.query(Plan).filter(
                Plan.user_id == user_id, Plan.is_active == True
            ).update({Plan.is_active: False}, synchronize_session=False)

            new_plan = Plan(
                id=str(uuid.uuid4()),
                photo_id=photo_id,
                user_id=user_id,
                data=enriched_plan,
                phases=enriched_plan.get("phases", {}),
                current_phase="week_1",
                current_week=1,
                is_active=True,
            )
            db_bg.add(new_plan)

        db_bg.commit()
        logger.info(f"✅ Background DeepSeek enrichment completed for photo {photo_id}")

    except Exception as exc:
        db_bg.rollback()
        logger.warning(f"Background DeepSeek enrichment failed for photo {photo_id}: {exc} — template data retained")
    finally:
        db_bg.close()


@router.post("/analyze/{photo_id}")
async def analyze_photo(
    photo_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Run face analysis and return results FAST (<2s typical).

    Strategy:
      1. Face detection + scoring (MediaPipe / mock) — always runs inline
      2. Template-based AI analysis and 90-day plan — generated in <1ms
      3. Response returned immediately to user
      4. DeepSeek enrichment runs in the BACKGROUND after the response is sent
         and silently updates the database if it succeeds.
    """
    start_time = time.perf_counter()

    # Get photo from DB
    photo = db.query(Photo).filter(Photo.id == photo_id, Photo.user_id == current_user.id).first()
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )

    # Download image bytes from Cloudinary
    import requests
    try:
        response = requests.get(photo.file_url, timeout=30)
        response.raise_for_status()
        image_bytes = response.content
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download image: {str(e)}"
        )

    # Step 1: Detect face landmarks
    face_result = detect_face_landmarks(image_bytes)
    if not face_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Face detection failed: {face_result.get('error', 'No face found')}"
        )

    landmarks = face_result["landmarks"]

    # Step 2: Calculate individual scores
    symmetry_score = calculate_symmetry(landmarks)
    skin_score = calculate_skin_score(landmarks, image_bytes)
    jawline_score = calculate_jawline_score(landmarks)
    eye_score = calculate_eye_score(landmarks)
    face_shape = get_face_shape(landmarks)

    # Generate overall score
    scores = {
        "symmetry": symmetry_score,
        "skin": skin_score,
        "jawline": jawline_score,
        "eyes": eye_score,
        "nose": 70.0,
        "lips": 75.0,
    }
    overall_score = generate_overall_score(scores)

    score_data = {
        "overall_score": overall_score,
        "symmetry_score": symmetry_score,
        "skin_score": skin_score,
        "jawline_score": jawline_score,
        "eye_score": eye_score,
        "face_shape": face_shape,
    }

    # Step 2.5: 6-category breakdown
    category_breakdown = get_category_breakdown(
        image_bytes=image_bytes,
        landmarks=landmarks,
        gender="male",
        overall_score=overall_score,
    )

    # ═══════════════════════════════════════════════════════════════
    # Step 3+4: INSTANT template-based analysis + plan (<1ms)
    # ═══════════════════════════════════════════════════════════════
    fallback_analysis = generate_fallback_analysis(score_data)
    fallback_plan = generate_fallback_plan(overall_score, gender="male")

    analysis_data = fallback_analysis.get("data", {})
    plan_data = fallback_plan

    # ═══════════════════════════════════════════════════════════════
    # Step 5: Update photo + plan in DB with template data immediately
    # ═══════════════════════════════════════════════════════════════
    photo.score = overall_score
    photo.symmetry_score = symmetry_score
    photo.skin_score = skin_score
    photo.jawline_score = jawline_score
    photo.eye_score = eye_score
    photo.face_shape = face_shape
    photo.strengths = analysis_data.get("strengths", [])
    photo.weaknesses = analysis_data.get("weaknesses", [])
    photo.analysis_details = {
        "category_breakdown": category_breakdown,
        "deepseek_analysis": {},
        "source": "template",
    }

    # Save plan
    existing_plan = db.query(Plan).filter(Plan.photo_id == photo.id).first()
    if existing_plan:
        existing_plan.data = plan_data
        existing_plan.updated_at = datetime.utcnow()
    else:
        new_plan = Plan(
            id=str(uuid.uuid4()),
            photo_id=photo.id,
            user_id=current_user.id,
            data=plan_data,
            phases=plan_data.get("phases", {}),
            current_phase="week_1",
            current_week=1,
        )
        db.add(new_plan)

    # ── Convert any NumPy types to Python native types ────────────
    # Face-service helpers (calculate_symmetry, etc.) may return
    # np.float64 / np.int64, which SQLAlchemy misinterprets as
    # PostgreSQL schema references ("np" schema).
    def _py(val):
        """Convert NumPy scalar/array to a plain Python value."""
        if val is None:
            return None
        if isinstance(val, (np.integer, np.floating)):
            return val.item()
        if isinstance(val, np.ndarray):
            return val.tolist()
        return val

    photo.score = _py(photo.score)
    photo.symmetry_score = _py(photo.symmetry_score)
    photo.skin_score = _py(photo.skin_score)
    photo.jawline_score = _py(photo.jawline_score)
    photo.eye_score = _py(photo.eye_score)
    # nose_score and lips_score are stored in analysis_details JSON only

    # Deep-clean any JSON fields so nested np scalars are purged
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

    photo.analysis_details = _json_safe(photo.analysis_details)
    # ──────────────────────────────────────────────────────────────

    db.commit()
    db.refresh(photo)

    # ═══════════════════════════════════════════════════════════════
    # Step 6: Enqueue DeepSeek enrichment as BACKGROUND TASK
    #         This runs AFTER the response is sent to the user.
    # ═══════════════════════════════════════════════════════════════
    background_tasks.add_task(
        _enrich_with_deepseek_background,
        photo_id=photo.id,
        user_id=current_user.id,
        score_data=score_data,
        category_breakdown=category_breakdown,
        fallback_analysis=fallback_analysis,
        fallback_plan=plan_data,
    )

    # Score labels
    overall_score_label = get_score_label(overall_score)
    score_labels = {
        "symmetry": get_score_label(symmetry_score),
        "skin": get_score_label(skin_score),
        "jawline": get_score_label(jawline_score),
        "eyes": get_score_label(eye_score),
        "nose": get_score_label(70.0),
        "lips": get_score_label(75.0),
    }

    end_time = time.perf_counter()
    elapsed_ms = (end_time - start_time) * 1000
    print(f"⚡ Analysis completed in {elapsed_ms:.0f}ms (DeepSeek enrichment queued in background)")

    return {
        "success": True,
        "processing_time_ms": round(elapsed_ms, 2),
        "photo_id": photo.id,
        "analysis": {
            "overall_score": overall_score,
            "overall_score_label": overall_score_label,
            "scores": {
                "symmetry": symmetry_score,
                "skin": skin_score,
                "jawline": jawline_score,
                "eyes": eye_score,
                "nose": 70.0,
                "lips": 75.0,
            },
            "score_labels": score_labels,
            "face_shape": face_shape,
            "strengths": analysis_data.get("strengths", []),
            "weaknesses": analysis_data.get("weaknesses", []),
            "improvement_potential": analysis_data.get("improvement_potential", "Up to +8 points in 90 days"),
            "category_breakdown": category_breakdown,
        },
        "recommendations": {
            "skincare": analysis_data.get("skincare_routine", []),
            "grooming": analysis_data.get("grooming_advice", ""),
            "exercise": analysis_data.get("exercise_tips", []),
            "diet": analysis_data.get("diet_advice", []),
            "products": analysis_data.get("recommended_products", []),
        },
        "action_plan": plan_data,
        "seven_day_plan": analysis_data.get("seven_day_plan", []),
    }
