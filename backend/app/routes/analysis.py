from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Photo, Plan
from app.dependencies import get_current_user, require_pro, require_elite
from app.services.score_calibration import compute_potential_score
from app.services.score_labels import get_score_label
from app.services.insights_service import (
    build_archetype,
    build_blueprint,
    build_forecast,
    build_glow_up_card,
    build_golden_ratio,
    rank_label,
)
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


@router.get("/{photo_id}/report")
async def get_full_report(
    photo_id: str,
    current_user: User = Depends(require_pro),
    db: Session = Depends(get_db)
):
    """Pro/Elite: full written report for a scored photo (gated by require_pro)."""
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.user_id == current_user.id
    ).first()

    if not photo or photo.score is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyzed photo not found"
        )

    details = photo.analysis_details or {}
    breakdown = details.get("category_breakdown") or {}
    if not isinstance(breakdown, dict):
        breakdown = {}

    categories = [
        {"key": k, "score": v, "label": k.replace("_", " ").title()}
        for k, v in breakdown.items()
    ]
    categories.sort(key=lambda c: c["score"])
    weakest = [c["key"] for c in categories[:3]]
    strongest = [c["key"] for c in categories[-3:]][::-1]

    deepseek = details.get("deepseek_analysis") or {}
    if not isinstance(deepseek, dict):
        deepseek = {}

    potential = compute_potential_score(photo.score)

    return {
        "photo_id": photo.id,
        "overall_score": photo.score,
        "potential_score": potential,
        "improvement_gap": round((potential or 0) - photo.score, 1),
        "face_shape": photo.face_shape,
        "categories": categories,
        "weakest_areas": weakest,
        "strongest_areas": strongest,
        "strengths": photo.strengths or [],
        "weaknesses": photo.weaknesses or [],
        "improvement_potential": details.get("improvement_potential", "Up to +8 points in 90 days"),
        "recommendations": {
            "skincare": deepseek.get("skincare_routine") or details.get("skincare_routine", []),
            "grooming": deepseek.get("grooming_advice") or details.get("grooming_advice", ""),
            "exercise": deepseek.get("exercise_tips") or details.get("exercise_tips", []),
            "diet": deepseek.get("diet_advice") or details.get("diet_advice", []),
        },
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


def _get_scored_photo(photo_id: str, current_user: User, db: Session) -> Photo:
    photo = db.query(Photo).filter(
        Photo.id == photo_id,
        Photo.user_id == current_user.id
    ).first()

    if not photo or photo.score is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyzed photo not found"
        )
    return photo


def _percentile(score: float, gender: str, user_id: str, db: Session) -> dict:
    """Where this user's score ranks among their peers (same gender when known)."""
    rows = (
        db.query(Photo.user_id, Photo.score, Photo.captured_at)
        .filter(Photo.score.isnot(None))
        .all()
    )

    latest: dict = {}
    for uid, s, ts in rows:
        if uid not in latest or (ts is not None and (latest[uid][1] is None or ts > latest[uid][1])):
            latest[uid] = (s, ts)

    uids = list(latest.keys())
    genders: dict = {}
    if uids:
        for u in db.query(User).filter(User.id.in_(uids)).all():
            genders[u.id] = (u.gender or "other").lower()

    peer_scores = [
        s for uid, (s, _) in latest.items()
        if uid != user_id and (gender == "other" or genders.get(uid, "other") == gender)
    ]
    if not peer_scores:
        peer_scores = [s for uid, (s, _) in latest.items() if uid != user_id]

    total = len(peer_scores)
    if total == 0:
        return {"percentile": None, "peer_count": 0, "gender": gender, "rank_label": rank_label(None)}

    below = sum(1 for s in peer_scores if s < score)
    equal = sum(1 for s in peer_scores if s == score)
    percentile = round((below + 0.5 * equal) / total * 100, 1)

    return {
        "percentile": percentile,
        "peer_count": total,
        "gender": gender,
        "rank_label": rank_label(percentile),
    }


@router.get("/{photo_id}/insights")
async def get_insights(
    photo_id: str,
    current_user: User = Depends(require_pro),
    db: Session = Depends(get_db)
):
    """Pro/Elite: Glow-Up Forecast, Percentile Rank and Look-Alike Archetype."""
    photo = _get_scored_photo(photo_id, current_user, db)
    details = photo.analysis_details or {}
    breakdown = details.get("category_breakdown") or {}
    if not isinstance(breakdown, dict):
        breakdown = {}

    gender = (current_user.gender or "other").lower()

    return {
        "photo_id": photo.id,
        "forecast": build_forecast(photo.score, current_user.current_day),
        "percentile": _percentile(photo.score, gender, current_user.id, db),
        "archetype": build_archetype(photo.score, photo.face_shape, gender, breakdown),
    }


@router.get("/{photo_id}/harmony")
async def get_harmony(
    photo_id: str,
    current_user: User = Depends(require_elite),
    db: Session = Depends(get_db)
):
    """Elite: Golden-Ratio Harmony Map, Weekly Blueprint and Shareable Card."""
    photo = _get_scored_photo(photo_id, current_user, db)
    details = photo.analysis_details or {}
    breakdown = details.get("category_breakdown") or {}
    if not isinstance(breakdown, dict):
        breakdown = {}

    gender = (current_user.gender or "other").lower()

    scores = {
        "symmetry": photo.symmetry_score,
        "skin": photo.skin_score,
        "jawline": photo.jawline_score,
        "eyes": photo.eye_score,
    }

    weakest = sorted(breakdown, key=lambda k: breakdown.get(k, 0))[:3] if breakdown else []
    archetype = build_archetype(photo.score, photo.face_shape, gender, breakdown)

    top_key = max(breakdown, key=lambda k: breakdown.get(k, 0)) if breakdown else None
    top_strength = top_key.replace("_", " ").title() if top_key else "natural balance"

    label = get_score_label(photo.score)["label"]

    return {
        "photo_id": photo.id,
        "golden_ratio": build_golden_ratio(breakdown, scores),
        "blueprint": build_blueprint(weakest, gender),
        "glow_up_card": build_glow_up_card(
            current_user.full_name,
            photo.score,
            label,
            archetype["name"],
            top_strength,
            current_user.current_day,
            current_user.subscription_tier,
        ),
    }