from fastapi import APIRouter, HTTPException, status, Depends, File, UploadFile
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Photo, Plan
from app.schemas import PhotoUploadResponse, APIResponse
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
from app.services.ai_service import analyze_face_with_deepseek
from app.services.plan_generator_service import generate_action_plan
from app.services.score_labels import get_score_label
from app.services.prediction_service import prediction_service
from app.config import settings
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/photos", tags=["Photos"])

@router.post("/upload", response_model=PhotoUploadResponse)
async def upload_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a photo for analysis.
    
    - Supported formats: JPG, PNG, HEIC
    - Max size: 10MB
    - Returns photo ID and URL
    """
    # Validate file type
    allowed_extensions = [".jpg", ".jpeg", ".png", ".heic"]
    file_ext = f".{file.filename.split('.')[-1].lower()}"
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size
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
    
    try:
        # Upload to Cloudinary
        file_url = upload_to_cloudinary(file_content, file.filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )
    
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

    # Save to database
    new_photo = Photo(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        file_url=file_url,
        file_size=file_size,
        file_type=file_ext,
        is_baseline=is_baseline,
        week_number=week_number,
    )

    # 🔮 Run ML prediction on uploaded image
    try:
        gender = getattr(current_user, "gender", None) or "male"
        prediction = prediction_service.predict(file_content, gender=gender)
        score = prediction.get("score_100", None)
        if score is not None:
            new_photo.score = score
    except Exception as e:
        logger.warning(f"Prediction failed for photo {new_photo.id}: {e}")

    db.add(new_photo)
    db.commit()
    db.refresh(new_photo)

    return PhotoUploadResponse(
        id=new_photo.id,
        user_id=new_photo.user_id,
        file_url=new_photo.file_url,
        score=new_photo.score,
        is_baseline=new_photo.is_baseline,
        week_number=new_photo.week_number,
        captured_at=new_photo.captured_at,
    )

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


@router.post("/analyze/{photo_id}")
async def analyze_photo(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run full face analysis on a photo:
    1. Extract facial landmarks with MediaPipe
    2. Calculate scores (symmetry, skin, jaw, eyes)
    3. Send to DeepSeek for AI analysis
    4. Generate 90-day action plan
    5. Save results to database
    """
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
        "nose": 70.0,  # Placeholder
        "lips": 75.0   # Placeholder
    }
    overall_score = generate_overall_score(scores)

    # Step 2.5: Calculate 6-category breakdown
    category_breakdown = get_category_breakdown(
        image_bytes=image_bytes,
        landmarks=landmarks,
        gender="male",  # Default - can be extended with user profile gender
        overall_score=overall_score,
    )

    # Step 3: Send to DeepSeek for AI analysis
    score_data = {
        "overall_score": overall_score,
        "symmetry_score": symmetry_score,
        "skin_score": skin_score,
        "jawline_score": jawline_score,
        "eye_score": eye_score,
        "face_shape": face_shape
    }
    deepseek_result = analyze_face_with_deepseek(score_data, photo.file_url)

    # Step 4: Generate 90-day action plan using new plan generator
    action_plan = generate_action_plan(
        score_data=score_data,
        category_breakdown=category_breakdown,
        user_profile={"gender": "male"},
    )

    # Step 5: Update photo score in database
    photo.score = overall_score
    photo.symmetry_score = symmetry_score
    photo.skin_score = skin_score
    photo.jawline_score = jawline_score
    photo.eye_score = eye_score
    photo.face_shape = face_shape

    # Store detailed analysis including category breakdown for later reuse
    photo.strengths = deepseek_result.get("data", {}).get("strengths", []) if deepseek_result.get("success") else []
    photo.weaknesses = deepseek_result.get("data", {}).get("weaknesses", []) if deepseek_result.get("success") else []
    photo.analysis_details = {
        "category_breakdown": category_breakdown,
        "deepseek_analysis": deepseek_result.get("data", {}) if deepseek_result.get("success") else {},
    }

    # Step 6: Save plan to database
    import json
    existing_plan = db.query(Plan).filter(Plan.photo_id == photo.id).first()
    if existing_plan:
        existing_plan.data = action_plan
        existing_plan.updated_at = datetime.utcnow()
    else:
        new_plan = Plan(
            id=str(uuid.uuid4()),
            photo_id=photo.id,
            user_id=current_user.id,
            data=action_plan,
            phases=action_plan.get("phases", {}),
            current_phase="week_1",
            current_week=1
        )
        db.add(new_plan)

    db.commit()
    db.refresh(photo)

    # Score labels for the overall and per-category scores
    overall_score_label = get_score_label(overall_score)
    score_labels = {
        "symmetry": get_score_label(symmetry_score),
        "skin": get_score_label(skin_score),
        "jawline": get_score_label(jawline_score),
        "eyes": get_score_label(eye_score),
        "nose": get_score_label(70.0),
        "lips": get_score_label(75.0),
    }

    # Build response
    deepseek_data = deepseek_result.get("data", {}) if deepseek_result.get("success") else {}

    return {
        "success": True,
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
                "lips": 75.0
            },
            "score_labels": score_labels,
            "face_shape": face_shape,
            "strengths": deepseek_data.get("strengths", []),
            "weaknesses": deepseek_data.get("weaknesses", []),
            "improvement_potential": deepseek_data.get("improvement_potential", "Up to +8 points in 90 days"),
            "category_breakdown": category_breakdown
        },
        "recommendations": {
            "skincare": deepseek_data.get("skincare_routine", []),
            "grooming": deepseek_data.get("grooming_advice", ""),
            "exercise": deepseek_data.get("exercise_tips", []),
            "diet": deepseek_data.get("diet_advice", []),
            "products": deepseek_data.get("recommended_products", [])
        },
        "action_plan": action_plan,
        "seven_day_plan": deepseek_data.get("seven_day_plan", [])
    }
