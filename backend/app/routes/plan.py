"""
Plan Routes — 90-day transformation plan management.

Psychological hooks for iOS widget/notification layer:
- Zeigarnik Effect: Show incomplete daily tasks to pull user back in
- Loss Aversion: Consecutive day streak tracking
- Progress Principle: Milestone celebrations at Day 7, 14, 21, 30, 45, 60, 75, 90
- Peak-End Rule: Day 30/60/90 photo comparison nudges
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Photo, Plan, UserCheckin
from app.dependencies import get_current_user
from app.schemas import CheckinLogRequest
from app.services.plan_generator_service import generate_fallback_plan, generate_action_plan
from app.services.face_analysis_service import get_category_breakdown
from datetime import datetime
import uuid

router = APIRouter(prefix="/plan", tags=["Plan"])


# ---------------------------------------------------------------------------
# GET /plan — Fetch the current user's active plan
# ---------------------------------------------------------------------------
@router.get("")
async def get_my_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the current user's active 90-day action plan.
    Returns plan with current phase, current week, tasks, milestones, and motivational content.
    """
    # Find the most recent active plan for this user
    plan = (
        db.query(Plan)
        .filter(Plan.user_id == current_user.id, Plan.is_active == True)
        .order_by(Plan.created_at.desc())
        .first()
    )

    if not plan:
        # No plan exists — return a hint that they need to analyse a photo first
        return {
            "has_plan": False,
            "message": "Upload and analyse your first photo to generate a personalised 90-day plan.",
            "plan": None,
        }

    # Get linked photo for baseline score
    photo = db.query(Photo).filter(Photo.id == plan.photo_id).first()

    # Build response
    plan_data = plan.data or {}
    phases = plan_data.get("phases", plan.phases or {})

    # Determine current day (estimate from plan created date if current_day is 0)
    current_day = plan.current_day or 0
    if current_day == 0 and plan.created_at:
        delta = (datetime.utcnow() - plan.created_at).days
        current_day = min(delta, 90)  # Cap at 90

    # Calculate current week
    if current_day > 0:
        current_week = ((current_day - 1) // 7) + 1
    else:
        current_week = 1

    # Determine current phase
    if current_day <= 30:
        current_phase = "phase_1"
    elif current_day <= 60:
        current_phase = "phase_2"
    else:
        current_phase = "phase_3"

    # Get current phase's weekly tasks
    current_phase_data = phases.get(current_phase, {})
    weekly_tasks = current_phase_data.get("weekly_tasks", [])

    # Get current week's tasks
    current_week_tasks = None
    for week_data in weekly_tasks:
        if week_data.get("week") == current_week:
            current_week_tasks = week_data
            break

    if not current_week_tasks and weekly_tasks:
        # Fallback: return the first week of the current phase
        current_week_tasks = weekly_tasks[0]

    # Get today's motivational quote
    motivational_quotes = plan_data.get("motivational_quotes", [])
    todays_quote = None
    for q in motivational_quotes:
        if q.get("day") == current_day:
            todays_quote = q
            break
    if not todays_quote and motivational_quotes:
        # Find the most recent past milestone
        recent_quotes = [q for q in motivational_quotes if q.get("day", 0) <= current_day]
        if recent_quotes:
            todays_quote = recent_quotes[-1]

    # Get upcoming milestone
    milestones = plan_data.get("milestones", {})
    upcoming_milestone = None
    milestone_days = [7, 14, 21, 30, 45, 60, 75, 90]
    for day in milestone_days:
        if current_day < day:
            upcoming_milestone = {
                "day": day,
                "days_remaining": day - current_day,
                "details": milestones.get(f"day_{day}", {}),
            }
            break

    # Calculate streak (days since plan started)
    days_since_start = 0
    if plan.created_at:
        days_since_start = (datetime.utcnow() - plan.created_at).days
    streak = min(days_since_start, 90)

    # Products
    products = plan_data.get("products", [])

    return {
        "has_plan": True,
        "plan_id": plan.id,
        "photo_id": plan.photo_id,
        "baseline_score": photo.score if photo else None,
        "total_days": plan_data.get("total_days", 90),
        "current": {
            "day": current_day,
            "week": current_week,
            "phase": current_phase,
            "phase_title": current_phase_data.get("title", ""),
            "phase_emotional_goal": current_phase_data.get("emotional_goal", ""),
            "focus_areas": current_phase_data.get("focus_areas", []),
        },
        "this_week": current_week_tasks,
        "todays_quote": todays_quote,
        "upcoming_milestone": upcoming_milestone,
        "streak": streak,
        "products": products,
        "bonus_tip": plan_data.get("bonus_tip", ""),
        "phases": {
            "phase_1": {
                "days": phases.get("phase_1", {}).get("days", "1-30"),
                "title": phases.get("phase_1", {}).get("title", ""),
                "complete": current_day >= 30,
            },
            "phase_2": {
                "days": phases.get("phase_2", {}).get("days", "31-60"),
                "title": phases.get("phase_2", {}).get("title", ""),
                "complete": current_day >= 60,
            },
            "phase_3": {
                "days": phases.get("phase_3", {}).get("days", "61-90"),
                "title": phases.get("phase_3", {}).get("title", ""),
                "complete": current_day >= 90,
            },
        },
    }


# ---------------------------------------------------------------------------
# POST /plan/checkin — Daily/weekly check-in (Zeigarnik & Loss Aversion hook)
# ---------------------------------------------------------------------------
@router.post("/checkin")
async def daily_checkin(
    payload: CheckinLogRequest = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Log a daily/weekly check-in.
    
    On the iOS side, this is triggered when the user:
    - Taps "Complete" on a daily task
    - Does a weekly check-in (uploading a new photo or filling notes)
    
    The iOS widget/notification layer uses the missed-checkin count
    to trigger the Zeigarnik Effect ("You have 3 tasks left today").
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
            detail="No active plan found. Analyse a photo first to generate a plan.",
        )

    # Calculate current day
    current_day = plan.current_day or 0
    if current_day == 0 and plan.created_at:
        delta = (datetime.utcnow() - plan.created_at).days
        current_day = min(delta, 90)

    # Advance day count
    new_day = current_day + 1 if current_day < 90 else 90

    # Update plan
    plan.current_day = new_day
    plan.current_week = ((new_day - 1) // 7) + 1

    # Determine phase
    if new_day <= 30:
        plan.current_phase = "phase_1"
    elif new_day <= 60:
        plan.current_phase = "phase_2"
    else:
        plan.current_phase = "phase_3"

    plan.updated_at = datetime.utcnow()

    # ── Plan Regeneration: Check if new photo analysis exists ──────
    # If the user uploaded and analyzed a new photo after the plan was
    # last updated, regenerate the action plan based on new scores.
    latest_analyzed_photo = (
        db.query(Photo)
        .filter(
            Photo.user_id == current_user.id,
            Photo.score.isnot(None),
        )
        .order_by(Photo.captured_at.desc())
        .first()
    )

    plan_regenerated = False
    if latest_analyzed_photo and latest_analyzed_photo.captured_at:
        # Check if the latest analysis is newer than the plan's last update
        last_plan_update = plan.updated_at or plan.created_at
        if latest_analyzed_photo.captured_at > last_plan_update:
            try:
                # Download image bytes for category re-analysis
                import requests as http_requests
                resp = http_requests.get(latest_analyzed_photo.file_url, timeout=15)
                if resp.status_code == 200:
                    # Detect face landmarks for category breakdown
                    from app.services.face_service import detect_face_landmarks
                    face_result = detect_face_landmarks(resp.content)
                    landmarks = face_result.get("landmarks") if face_result.get("success") else None

                    # Get fresh category breakdown
                    fresh_category_breakdown = None
                    if landmarks:
                        fresh_category_breakdown = get_category_breakdown(
                            image_bytes=resp.content,
                            landmarks=landmarks,
                            gender=current_user.gender or "male",
                            overall_score=latest_analyzed_photo.score or 75.0,
                        )

                    # Build score data from the latest photo
                    score_data = {
                        "overall_score": latest_analyzed_photo.score or 75.0,
                        "symmetry_score": latest_analyzed_photo.symmetry_score or 65.0,
                        "skin_score": latest_analyzed_photo.skin_score or 65.0,
                        "jawline_score": latest_analyzed_photo.jawline_score or 65.0,
                        "eye_score": latest_analyzed_photo.eye_score or 65.0,
                        "face_shape": latest_analyzed_photo.face_shape or "oval",
                    }

                    # Regenerate plan
                    new_action_plan = generate_action_plan(
                        score_data=score_data,
                        category_breakdown=fresh_category_breakdown or {},
                        user_profile={"gender": current_user.gender or "male"},
                    )

                    # Update plan with new data, preserving day/week/phase progress
                    plan.data = new_action_plan
                    plan.phases = new_action_plan.get("phases", {})
                    plan.photo_id = latest_analyzed_photo.id  # Link to latest photo
                    plan_regenerated = True
            except Exception:
                pass  # Silently skip regeneration on error — don't break the check-in

    # Create check-in record
    checkin = UserCheckin(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        week_number=plan.current_week,
        completed_tasks=payload.completed_tasks if payload else [],
        notes=payload.notes if payload else "",
    )
    db.add(checkin)

    # If plan completed (day 90)
    if new_day >= 90:
        plan.is_active = False
        plan.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(plan)

    # Calculate remaining tasks today (Zeigarnik hook for iOS notifications)
    plan_data = plan.data or {}
    phases = plan_data.get("phases", plan.phases or {})
    current_phase = phases.get(plan.current_phase, {})
    weekly_tasks = current_phase.get("weekly_tasks", [])
    current_week_tasks = None
    for week_data in weekly_tasks:
        if week_data.get("week") == plan.current_week:
            current_week_tasks = week_data
            break

    total_tasks = len(current_week_tasks.get("daily_tasks", [])) if current_week_tasks else 0
    completed_count = len(payload.completed_tasks) if payload and payload.completed_tasks else 0
    remaining_tasks = max(0, total_tasks - completed_count)

    return {
        "success": True,
        "current_day": new_day,
        "current_week": plan.current_week,
        "current_phase": plan.current_phase,
        "days_remaining": 90 - new_day,
        "total_tasks_today": total_tasks,
        "tasks_completed": completed_count,
        "tasks_remaining": remaining_tasks,
        "is_plan_complete": new_day >= 90,
        # Streak data for Loss Aversion hook
        "streak": new_day,
        "streak_message": f"{new_day} day streak — don't break it!" if new_day > 0 else "Start your streak today!",
        # Plan regeneration info
        "plan_regenerated": plan_regenerated,
        "regeneration_photo_id": latest_analyzed_photo.id if plan_regenerated else None,
    }


# ---------------------------------------------------------------------------
# GET /plan/progress — Progress summary (Progress Principle hook)
# ---------------------------------------------------------------------------
@router.get("/progress")
async def get_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get progress summary: current score, baseline comparison, completed milestones.
    
    Used by the iOS progress screen / notification layer. 
    Implements the Progress Principle — celebrate every small win.
    """
    # Find active plan
    plan = (
        db.query(Plan)
        .filter(Plan.user_id == current_user.id, Plan.is_active == True)
        .order_by(Plan.created_at.desc())
        .first()
    )

    if not plan:
        return {
            "has_plan": False,
            "message": "No active plan. Start by uploading and analysing your first photo.",
        }

    # Get baseline photo
    baseline_photo = (
        db.query(Photo)
        .filter(Photo.user_id == current_user.id, Photo.is_baseline == True)
        .first()
    )

    # Get latest photo with a score
    latest_photo = (
        db.query(Photo)
        .filter(Photo.user_id == current_user.id, Photo.score.isnot(None))
        .order_by(Photo.captured_at.desc())
        .first()
    )

    # Calculate score change
    baseline_score = baseline_photo.score if baseline_photo else None
    current_score = latest_photo.score if latest_photo else None
    score_change = None
    if baseline_score is not None and current_score is not None:
        score_change = round(current_score - baseline_score, 1)

    # Calculate current day
    current_day = plan.current_day or 0
    if current_day == 0 and plan.created_at:
        delta = (datetime.utcnow() - plan.created_at).days
        current_day = min(delta, 90)

    # Completed milestones
    plan_data = plan.data or {}
    milestones = plan_data.get("milestones", {})
    milestone_days = [7, 14, 21, 30, 45, 60, 75, 90]
    completed_milestones = []
    upcoming_milestones = []
    for day in milestone_days:
        milestone = milestones.get(f"day_{day}", {})
        if current_day >= day:
            completed_milestones.append({
                "day": day,
                "title": milestone.get("title", f"Day {day}"),
                "achieved": True,
            })
        else:
            upcoming_milestones.append({
                "day": day,
                "title": milestone.get("title", f"Day {day}"),
                "days_remaining": day - current_day,
                "achieved": False,
            })

    # Check-ins count
    checkin_count = (
        db.query(UserCheckin)
        .filter(UserCheckin.user_id == current_user.id)
        .count()
    )

    return {
        "has_plan": True,
        "current_day": current_day,
        "days_remaining": 90 - current_day,
        "percent_complete": round((current_day / 90) * 100, 1),
        "baseline_score": baseline_score,
        "current_score": current_score,
        "score_change": score_change,
        "trend": "improving" if (score_change or 0) > 0 else ("declining" if (score_change or 0) < 0 else "stable"),
        "checkins_logged": checkin_count,
        "completed_milestones": completed_milestones,
        "upcoming_milestones": upcoming_milestones[:3],
        "next_photo_reminder": get_next_photo_reminder(current_day),
    }


# ---------------------------------------------------------------------------
# Helper: Next photo reminder (Peak-End Rule)
# ---------------------------------------------------------------------------
def get_next_photo_reminder(current_day: int) -> dict:
    """
    Determine when the next progress photo should be taken.
    Photos are recommended at Day 30, Day 60, and Day 90 (Peak-End Rule).
    """
    photo_checkpoints = [30, 60, 90]
    for day in photo_checkpoints:
        if current_day < day:
            return {
                "day": day,
                "days_remaining": day - current_day,
                "message": f"Your next progress photo is at Day {day}. "
                           f"Take a photo in good natural lighting for the best comparison.",
            }
    return {
        "day": 90,
        "days_remaining": 0,
        "message": "🎉 You've reached Day 90! Take your final progress photo to see your full transformation.",
    }