from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Photo, Plan
from app.dependencies import get_current_user
from datetime import datetime

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.get("/{photo_id}")
async def get_analysis(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get analysis results for a specific photo.
    """
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.user_id == current_user.id
    ).first()

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )

    if photo.score is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This photo has not been analyzed yet"
        )

    return {
        "photo_id": photo.id,
        "file_url": photo.file_url,
        "scores": {
            "overall": photo.score,
            "symmetry": photo.symmetry_score,
            "skin": photo.skin_score,
            "jawline": photo.jawline_score,
            "eyes": photo.eye_score
        },
        "face_shape": photo.face_shape,
        "is_baseline": photo.is_baseline,
        "analyzed_at": photo.captured_at
    }


@router.get("/{photo_id}/plan")
async def get_action_plan(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the 90-day action plan for a photo's analysis.
    """
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.user_id == current_user.id
    ).first()

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )

    plan = db.query(Plan).filter(Plan.photo_id == photo.id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No action plan found. Please analyze the photo first."
        )

    return {
        "plan_id": plan.id,
        "photo_id": plan.photo_id,
        "current_phase": plan.current_phase,
        "current_week": plan.current_week,
        "phases": plan.phases,
        "products": plan.data.get("products", []),
        "weaknesses": plan.data.get("weaknesses", []),
        "strengths": plan.data.get("strengths", []),
        "total_days": plan.data.get("total_days", 90)
    }


@router.put("/{photo_id}/plan/progress")
async def update_plan_progress(
    photo_id: str,
    current_phase: str = None,
    current_week: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the user's progress on their action plan.
    """
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.user_id == current_user.id
    ).first()

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )

    plan = db.query(Plan).filter(Plan.photo_id == photo.id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No action plan found"
        )

    if current_phase:
        plan.current_phase = current_phase
    if current_week:
        plan.current_week = current_week

    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)

    return {
        "plan_id": plan.id,
        "current_phase": plan.current_phase,
        "current_week": plan.current_week,
        "updated_at": plan.updated_at
    }


@router.get("/progress/all")
async def get_all_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all analysis history and progress for the current user.
    Returns a progress timeline with score changes over time.
    """
    photos = db.query(Photo).filter(
        Photo.user_id == current_user.id,
        Photo.score.isnot(None)
    ).order_by(Photo.captured_at.asc()).all()

    if not photos:
        return {"photos": [], "progress": None, "message": "No analyzed photos yet"}

    # Build timeline
    timeline = []
    for photo in photos:
        plan = db.query(Plan).filter(Plan.photo_id == photo.id).first()
        timeline.append({
            "photo_id": photo.id,
            "score": photo.score,
            "face_shape": photo.face_shape,
            "is_baseline": photo.is_baseline,
            "date": photo.captured_at,
            "plan_phase": plan.current_phase if plan else None,
            "plan_week": plan.current_week if plan else None
        })

    # Calculate progress
    baseline = photos[0] if photos else None
    latest = photos[-1] if photos else None

    progress = None
    if baseline and latest and baseline.score and latest.score:
        score_change = latest.score - baseline.score
        progress = {
            "baseline_score": baseline.score,
            "current_score": latest.score,
            "score_change": round(score_change, 1),
            "trend": "improving" if score_change > 0 else ("declining" if score_change < 0 else "stable"),
            "total_photos_analyzed": len(photos)
        }

    return {
        "photos": timeline,
        "progress": progress
    }


@router.get("/{photo_id}/recommendations")
async def get_recommendations(
    photo_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized recommendations from the AI analysis.
    """
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.user_id == current_user.id
    ).first()

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )

    plan = db.query(Plan).filter(Plan.photo_id == photo.id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No recommendations found"
        )

    data = plan.data or {}

    return {
        "photo_id": photo.id,
        "skincare_routine": data.get("skincare_routine", []),
        "grooming_advice": data.get("grooming_advice", ""),
        "exercise_tips": data.get("exercise_tips", []),
        "diet_advice": data.get("diet_advice", []),
        "recommended_products": data.get("recommended_products", []),
        "seven_day_plan": data.get("seven_day_plan", [])
    }