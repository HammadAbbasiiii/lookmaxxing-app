"""
Progress Routes — User progress tracking and engagement.
Psychological hooks: streak (Loss Aversion), milestones (Progress Principle),
check-in logging (Zeigarnik Effect), photo comparisons (Peak-End Rule).

Endpoints:
- GET  /progress/history       → score history over time (chart data)
- GET  /progress/checkins       → all check-in records
- POST /progress/checkin        → log daily check-in (updates streak, milestones)
- GET  /progress/milestones     → upcoming & completed milestones
- GET  /progress/streak         → current streak info
- GET  /progress/photos          → all progress photos (baseline + check-ins)
- GET  /progress/photos/baseline → baseline photo
- GET  /progress/photos/latest   → latest check-in photo
- GET  /progress/photos/compare  → baseline vs latest comparison
- POST /progress/photos/upload   → upload a check-in photo
"""

from fastapi import APIRouter, HTTPException, status, Depends, File, UploadFile
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Photo, Plan, UserCheckin
from app.schemas import CheckinLogRequest, CheckinRecord, PhotoUploadResponse
from app.dependencies import get_current_user
from app.services.upload_service import upload_to_cloudinary
from app.config import settings
from datetime import datetime, date
import uuid

router = APIRouter(prefix="/progress", tags=["Progress"])

# ═══════════════════════════════════════════════════════════════════
# MILESTONE MAP — psychological celebration moments (Peak-End Rule)
# ═══════════════════════════════════════════════════════════════════
MILESTONES = {
    1: {
        "title": "Your Journey Begins",
        "emoji": "🚀",
        "message": "The first step is always the hardest. You did it.",
    },
    7: {
        "title": "One Week Strong",
        "emoji": "💪",
        "message": "You've been consistent for 7 days. This is how habits are built.",
    },
    14: {
        "title": "Two Weeks",
        "emoji": "🔥",
        "message": "You're building momentum. Keep going.",
    },
    21: {
        "title": "Three Weeks",
        "emoji": "⚡",
        "message": "Most people give up by now. You're not most people.",
    },
    30: {
        "title": "One Month!",
        "emoji": "🏆",
        "message": "You've completed Phase 1. You're 1/3 of the way there!",
    },
    45: {
        "title": "Halfway Point",
        "emoji": "🎯",
        "message": "You're halfway through your 90-day transformation.",
    },
    60: {
        "title": "Two Months",
        "emoji": "⭐",
        "message": "You're in the top 20% of users. Don't stop now.",
    },
    75: {
        "title": "Three-Quarter Mark",
        "emoji": "🏁",
        "message": "You're almost there. The finish line is in sight.",
    },
    90: {
        "title": "Transformation Complete!",
        "emoji": "🎉",
        "message": "You did it! Look at your transformation. You're a new person.",
    },
}

MILESTONE_DAYS = sorted(MILESTONES.keys())


# ═══════════════════════════════════════════════════════════════════
# Helper: update streak (Loss Aversion engine)
# ═══════════════════════════════════════════════════════════════════
def _update_streak(user: User) -> dict:
    """Update streak counters after a check-in. Returns streak state."""
    today = datetime.utcnow().date()
    last_checkin = user.last_checkin_date.date() if user.last_checkin_date else None

    if last_checkin == today:
        # Already checked in today — no change
        return {
            "streak_updated": False,
            "current_streak": user.current_streak,
            "longest_streak": user.longest_streak,
        }

    if last_checkin and (today - last_checkin).days == 1:
        # Consecutive day — extend streak
        user.current_streak += 1
    elif last_checkin and (today - last_checkin).days > 1:
        # Streak broken — reset
        user.current_streak = 1
    else:
        # First ever check-in
        user.current_streak = 1

    # Update longest streak record
    if user.current_streak > user.longest_streak:
        user.longest_streak = user.current_streak

    user.total_checkins += 1
    user.last_checkin_date = datetime.utcnow()

    return {
        "streak_updated": True,
        "current_streak": user.current_streak,
        "longest_streak": user.longest_streak,
    }


def _check_milestone(current_day: int) -> dict | None:
    """If current_day is exactly a milestone day, return the milestone data."""
    if current_day in MILESTONES:
        m = MILESTONES[current_day]
        return {"day": current_day, **m}
    return None


# ═══════════════════════════════════════════════════════════════════
# GET /progress/history — score history for charts
# ═══════════════════════════════════════════════════════════════════
@router.get("/history")
async def get_score_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return score history over time — used to render the progress chart on iOS.
    Each data point = a scored photo + the plan day it was taken on.
    """
    photos = (
        db.query(Photo)
        .filter(Photo.user_id == current_user.id, Photo.score.isnot(None))
        .order_by(Photo.captured_at.asc())
        .all()
    )

    if not photos:
        return {"has_data": False, "history": [], "message": "No scored photos yet."}

    # Determine current overall score from latest
    latest_photo = photos[-1]
    initial_score = photos[0].score

    history = []
    for p in photos:
        history.append(
            {
                "date": p.captured_at.isoformat() if p.captured_at else None,
                "score": round(p.score, 1) if p.score else None,
                "week_number": p.week_number,
                "is_baseline": p.is_baseline,
                "photo_id": p.id,
            }
        )

    return {
        "has_data": True,
        "initial_score": round(initial_score, 1) if initial_score else None,
        "current_score": round(latest_photo.score, 1) if latest_photo.score else None,
        "improvement": (
            round(latest_photo.score - initial_score, 1)
            if latest_photo.score and initial_score
            else 0
        ),
        "data_points": len(history),
        "history": history,
    }


# ═══════════════════════════════════════════════════════════════════
# GET /progress/checkins — all check-in records
# ═══════════════════════════════════════════════════════════════════
@router.get("/checkins")
async def get_checkins(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all check-in records for the current user.
    """
    checkins = (
        db.query(UserCheckin)
        .filter(UserCheckin.user_id == current_user.id)
        .order_by(UserCheckin.created_at.desc())
        .all()
    )
    return checkins


# ═══════════════════════════════════════════════════════════════════
# POST /progress/checkin — log a daily check-in
# ═══════════════════════════════════════════════════════════════════
@router.post("/checkin")
async def log_checkin(
    payload: CheckinLogRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Log a daily check-in.

    What happens:
    1. Mark today's tasks as complete
    2. Increment total_checkins
    3. Update streak (consecutive days → increment, else reset)
    4. If milestone day → trigger celebration
    5. Save check-in record
    """
    # Find active plan
    plan = (
        db.query(Plan)
        .filter(Plan.user_id == current_user.id, Plan.is_active == True)
        .order_by(Plan.created_at.desc())
        .first()
    )

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active plan found. Analyse a photo first.",
        )

    # Determine current day
    current_day = plan.current_day or 0
    if current_day == 0 and plan.created_at:
        delta = (datetime.utcnow() - plan.created_at).days
        current_day = min(delta, 90)

    # Advance day
    new_day = current_day + 1 if current_day < 90 else 90

    # Update plan
    plan.current_day = new_day
    plan.current_week = ((new_day - 1) // 7) + 1

    if new_day <= 30:
        plan.current_phase = "phase_1"
    elif new_day <= 60:
        plan.current_phase = "phase_2"
    else:
        plan.current_phase = "phase_3"

    plan.updated_at = datetime.utcnow()

    # Update user streak
    streak_result = _update_streak(current_user)
    current_user.current_day = new_day

    # Check milestone
    milestone = _check_milestone(new_day)

    # Create check-in record
    checkin = UserCheckin(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        week_number=plan.current_week,
        completed_tasks=payload.completed_tasks if payload else [],
        notes=payload.notes if payload else "",
    )
    db.add(checkin)

    # If plan completed
    if new_day >= 90:
        plan.is_active = False
        plan.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(plan)

    # Calculate tasks remaining (Zeigarnik hook)
    plan_data = plan.data or {}
    phases = plan_data.get("phases", plan.phases or {})
    current_phase = phases.get(plan.current_phase, {})
    weekly_tasks = current_phase.get("weekly_tasks", [])
    current_week_tasks = None
    for week_data in weekly_tasks:
        if week_data.get("week") == plan.current_week:
            current_week_tasks = week_data
            break

    total_tasks = (
        len(current_week_tasks.get("daily_tasks", [])) if current_week_tasks else 0
    )
    completed_count = len(payload.completed_tasks) if payload and payload.completed_tasks else 0
    remaining_tasks = max(0, total_tasks - completed_count)

    response = {
        "success": True,
        "current_day": new_day,
        "current_week": plan.current_week,
        "current_phase": plan.current_phase,
        "days_remaining": 90 - new_day,
        "progress_percentage": round((new_day / 90) * 100, 1),
        "total_tasks_today": total_tasks,
        "tasks_completed": completed_count,
        "tasks_remaining": remaining_tasks,
        "is_plan_complete": new_day >= 90,
        "streak": current_user.current_streak,
        "streak_message": (
            f"{current_user.current_streak} day streak — don't break it!"
            if current_user.current_streak > 0
            else "Start your streak today!"
        ),
        "longest_streak": current_user.longest_streak,
        "total_checkins": current_user.total_checkins,
    }

    if milestone:
        response["milestone"] = milestone

    return response


# ═══════════════════════════════════════════════════════════════════
# GET /progress/milestones — upcoming & completed milestones
# ═══════════════════════════════════════════════════════════════════
@router.get("/milestones")
async def get_milestones(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get upcoming and completed milestones based on current plan progress.
    """
    plan = (
        db.query(Plan)
        .filter(Plan.user_id == current_user.id, Plan.is_active == True)
        .order_by(Plan.created_at.desc())
        .first()
    )

    current_day = 0
    if plan:
        current_day = plan.current_day or 0
        if current_day == 0 and plan.created_at:
            delta = (datetime.utcnow() - plan.created_at).days
            current_day = min(delta, 90)

    completed = []
    upcoming = []
    next_milestone = None

    for day in MILESTONE_DAYS:
        m = MILESTONES[day]
        if current_day >= day:
            completed.append({"day": day, **m, "achieved": True})
        else:
            upcoming.append(
                {
                    "day": day,
                    **m,
                    "achieved": False,
                    "days_until": day - current_day,
                }
            )
            if next_milestone is None:
                next_milestone = {
                    "day": day,
                    **m,
                    "days_until": day - current_day,
                }

    return {
        "current_day": current_day,
        "next_milestone": next_milestone,
        "completed": completed,
        "upcoming": upcoming,
    }


# ═══════════════════════════════════════════════════════════════════
# GET /progress/streak — current streak info (Loss Aversion)
# ═══════════════════════════════════════════════════════════════════
@router.get("/streak")
async def get_streak(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get current streak information — used for iOS widget & notification layer.
    Implements Loss Aversion: users fear losing their streak.
    """
    # If last check-in was more than 1 day ago, streak is broken
    if current_user.last_checkin_date:
        days_since = (datetime.utcnow().date() - current_user.last_checkin_date.date()).days
        if days_since > 1:
            current_user.current_streak = 0
            db.commit()

    checked_in_today = False
    if current_user.last_checkin_date:
        checked_in_today = (
            current_user.last_checkin_date.date() == datetime.utcnow().date()
        )

    return {
        "current_streak": current_user.current_streak,
        "longest_streak": current_user.longest_streak,
        "total_checkins": current_user.total_checkins,
        "checked_in_today": checked_in_today,
        "last_checkin": (
            current_user.last_checkin_date.isoformat()
            if current_user.last_checkin_date
            else None
        ),
        "message": (
            f"🔥 {current_user.current_streak} day streak! Don't break it."
            if current_user.current_streak > 0
            else "Start your streak today!"
        ),
    }


# ═══════════════════════════════════════════════════════════════════
# GET /progress/photos — all progress photos
# ═══════════════════════════════════════════════════════════════════
@router.get("/photos")
async def get_progress_photos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get all progress photos (baseline + weekly check-ins) ordered by date.
    """
    photos = (
        db.query(Photo)
        .filter(Photo.user_id == current_user.id)
        .order_by(Photo.captured_at.asc())
        .all()
    )

    response = []
    for p in photos:
        response.append(
            {
                "id": p.id,
                "file_url": p.file_url,
                "score": p.score,
                "is_baseline": p.is_baseline,
                "week_number": p.week_number,
                "captured_at": p.captured_at.isoformat() if p.captured_at else None,
            }
        )

    return {
        "total": len(response),
        "photos": response,
        "has_baseline": any(p.is_baseline for p in photos),
    }


# ═══════════════════════════════════════════════════════════════════
# GET /progress/photos/baseline — baseline photo
# ═══════════════════════════════════════════════════════════════════
@router.get("/photos/baseline")
async def get_baseline_photo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the user's baseline photo (first photo ever uploaded).
    """
    photo = (
        db.query(Photo)
        .filter(Photo.user_id == current_user.id, Photo.is_baseline == True)
        .first()
    )

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No baseline photo found. Upload your first photo.",
        )

    return {
        "id": photo.id,
        "file_url": photo.file_url,
        "score": photo.score,
        "captured_at": photo.captured_at.isoformat() if photo.captured_at else None,
    }


# ═══════════════════════════════════════════════════════════════════
# GET /progress/photos/latest — latest check-in photo
# ═══════════════════════════════════════════════════════════════════
@router.get("/photos/latest")
async def get_latest_photo(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the most recent check-in photo with a score.
    """
    photo = (
        db.query(Photo)
        .filter(Photo.user_id == current_user.id, Photo.score.isnot(None))
        .order_by(Photo.captured_at.desc())
        .first()
    )

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No scored photos found.",
        )

    return {
        "id": photo.id,
        "file_url": photo.file_url,
        "score": photo.score,
        "is_baseline": photo.is_baseline,
        "week_number": photo.week_number,
        "captured_at": photo.captured_at.isoformat() if photo.captured_at else None,
    }


# ═══════════════════════════════════════════════════════════════════
# GET /progress/photos/compare — baseline vs latest side-by-side
# ═══════════════════════════════════════════════════════════════════
@router.get("/photos/compare")
async def compare_photos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return baseline and latest photo for side-by-side comparison (Peak-End Rule).
    Includes score change to quantify the transformation.
    """
    baseline = (
        db.query(Photo)
        .filter(Photo.user_id == current_user.id, Photo.is_baseline == True)
        .first()
    )

    latest = (
        db.query(Photo)
        .filter(
            Photo.user_id == current_user.id,
            Photo.score.isnot(None),
            Photo.is_baseline == False,
        )
        .order_by(Photo.captured_at.desc())
        .first()
    )

    if not baseline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No baseline photo found.",
        )

    score_change = None
    if baseline.score is not None and latest and latest.score is not None:
        score_change = round(latest.score - baseline.score, 1)

    return {
        "baseline": {
            "id": baseline.id,
            "file_url": baseline.file_url,
            "score": baseline.score,
            "captured_at": (
                baseline.captured_at.isoformat() if baseline.captured_at else None
            ),
        },
        "latest": {
            "id": latest.id if latest else None,
            "file_url": latest.file_url if latest else None,
            "score": latest.score if latest else None,
            "week_number": latest.week_number if latest else None,
            "captured_at": (
                latest.captured_at.isoformat()
                if latest and latest.captured_at
                else None
            ),
        }
        if latest
        else None,
        "score_change": score_change,
        "trend": (
            "improving"
            if score_change and score_change > 0
            else ("declining" if score_change and score_change < 0 else "stable")
        ),
        "weeks_progressed": latest.week_number - 1 if latest else 0,
    }


# ═══════════════════════════════════════════════════════════════════
# POST /progress/photos/upload — upload a check-in progress photo
# ═══════════════════════════════════════════════════════════════════
@router.post("/photos/upload")
async def upload_progress_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a progress check-in photo.

    Determines the correct week_number based on the user's plan progress.
    After upload, the photo is NOT automatically analysed — the client calls
    /photos/analyze/{photo_id} separately.
    """
    # Validate file
    allowed_extensions = [".jpg", ".jpeg", ".png", ".heic"]
    file_ext = f".{file.filename.split('.')[-1].lower()}"
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format. Allowed: {', '.join(allowed_extensions)}",
        )

    file_size = 0
    file_content = b""
    chunk_size = 1024 * 1024
    while chunk := await file.read(chunk_size):
        file_size += len(chunk)
        file_content += chunk
        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Max: {settings.MAX_FILE_SIZE_MB}MB",
            )

    # Upload
    try:
        file_url = upload_to_cloudinary(file_content, file.filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        )

    # Determine week_number from plan progress
    plan = (
        db.query(Plan)
        .filter(Plan.user_id == current_user.id, Plan.is_active == True)
        .order_by(Plan.created_at.desc())
        .first()
    )

    if plan and plan.current_week:
        week_number = plan.current_week
    else:
        # Fallback: count existing photos + 1
        photo_count = (
            db.query(Photo).filter(Photo.user_id == current_user.id).count()
        )
        week_number = photo_count + 1

    # Determine if baseline
    existing_photos = (
        db.query(Photo).filter(Photo.user_id == current_user.id).count()
    )
    is_baseline = existing_photos == 0

    # Save
    new_photo = Photo(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        file_url=file_url,
        file_size=file_size,
        file_type=file_ext,
        is_baseline=is_baseline,
        week_number=week_number,
    )
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