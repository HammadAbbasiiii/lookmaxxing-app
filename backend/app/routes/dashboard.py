"""
Dashboard Routes — unified summary endpoint for the iOS home screen.
Returns profile, plan, progress, milestones, and next action in one API call.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Photo, Plan, UserCheckin
from app.dependencies import get_current_user
from app.services.score_labels import get_score_label
from app.services.progress_engine import compute_current_day
from datetime import datetime

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# Mile stone map (same as in progress routes, kept independent)
MILESTONES = {
    1: {"title": "Your Journey Begins", "emoji": "🚀", "message": "The first step is always the hardest. You did it."},
    7: {"title": "One Week Strong", "emoji": "💪", "message": "You've been consistent for 7 days. This is how habits are built."},
    14: {"title": "Two Weeks", "emoji": "🔥", "message": "You're building momentum. Keep going."},
    21: {"title": "Three Weeks", "emoji": "⚡", "message": "Most people give up by now. You're not most people."},
    30: {"title": "One Month!", "emoji": "🏆", "message": "You've completed Phase 1. You're 1/3 of the way there!"},
    45: {"title": "Halfway Point", "emoji": "🎯", "message": "You're halfway through your 90-day transformation."},
    60: {"title": "Two Months", "emoji": "⭐", "message": "You're in the top 20% of users. Don't stop now."},
    75: {"title": "Three-Quarter Mark", "emoji": "🏁", "message": "You're almost there. The finish line is in sight."},
    90: {"title": "Transformation Complete!", "emoji": "🎉", "message": "You did it! Look at your transformation. You're a new person."},
}
MILESTONE_DAYS = [1, 7, 14, 21, 30, 45, 60, 75, 90]


@router.get("")
async def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unified dashboard endpoint. Returns all data needed for the iOS home screen
    in a single API call: profile, plan, progress, milestones, and next action.

    Response shape:
    {
        "profile": {...},
        "plan": {
            "current_day": 45, "total_days": 90, "progress_percentage": 50,
            "days_remaining": 45, "phase": "Building"
        },
        "progress": {
            "initial_score": 75.0, "current_score": 84.6, "improvement": 9.6,
            "current_streak": 7, "longest_streak": 12, "total_checkins": 15
        },
        "milestones": {
            "next": {"day": 60, "label": "Two Months", "days_until": 15},
            "completed": [...]
        },
        "next_action": {
            "task": "Apply Vitamin C serum (AM)",
            "time": "Morning"
        }
    }
    """
    # ── Profile ──────────────────────────────────────────────────
    profile = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "age": current_user.age,
        "gender": current_user.gender,
        "goals": current_user.goals,
        "onboarding_completed": current_user.onboarding_completed,
        "subscription_tier": current_user.subscription_tier,
        "is_subscribed": current_user.is_subscribed,
    }

    # ── Plan ─────────────────────────────────────────────────────
    plan = (
        db.query(Plan)
        .filter(Plan.user_id == current_user.id, Plan.is_active == True)
        .order_by(Plan.created_at.desc())
        .first()
    )

    plan_info = None
    if plan:
        current_day = compute_current_day(plan)

        plan_info = {
            "has_plan": True,
            "plan_id": plan.id,
            "current_day": current_day,
            "total_days": plan.total_days or 90,
            "progress_percentage": round((current_day / 90) * 100, 1) if current_day > 0 else 0,
            "days_remaining": max(0, 90 - current_day),
            "current_week": max(1, ((current_day - 1) // 7) + 1),
            "current_phase": plan.current_phase or (
                "phase_1" if current_day <= 30 else ("phase_2" if current_day <= 60 else "phase_3")
            ),
            "is_active": plan.is_active,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
        }
    else:
        plan_info = {
            "has_plan": False,
            "message": "Upload and analyse your first photo to start your 90-day transformation.",
        }

    # ── Progress ─────────────────────────────────────────────────
    baseline_photo = (
        db.query(Photo)
        .filter(Photo.user_id == current_user.id, Photo.is_baseline == True)
        .first()
    )
    latest_photo = (
        db.query(Photo)
        .filter(Photo.user_id == current_user.id, Photo.score.isnot(None))
        .order_by(Photo.captured_at.desc())
        .first()
    )

    initial_score = baseline_photo.score if baseline_photo else None
    current_score = latest_photo.score if latest_photo else None
    improvement = None
    if initial_score is not None and current_score is not None:
        improvement = round(current_score - initial_score, 1)

    # Fix broken streak
    if current_user.last_checkin_date:
        days_since = (datetime.utcnow().date() - current_user.last_checkin_date.date()).days
        if days_since > 1:
            current_user.current_streak = 0
            db.commit()

    checked_in_today = (
        current_user.last_checkin_date is not None
        and current_user.last_checkin_date.date() == datetime.utcnow().date()
    )

    # Score labels for dashboard display
    initial_score_label = get_score_label(initial_score) if initial_score is not None else None
    current_score_label = get_score_label(current_score) if current_score is not None else None

    # Per-category labels from latest analysis
    category_labels = None
    if latest_photo and latest_photo.analysis_details and isinstance(latest_photo.analysis_details, dict):
        breakdown = latest_photo.analysis_details.get("category_breakdown", {})
        if breakdown:
            category_labels = {
                cat: get_score_label(data["score"]) if isinstance(data, dict) and "score" in data else None
                for cat, data in breakdown.items()
                if cat not in ("heuristic",) and isinstance(data, dict)
            }

    progress_info = {
        "initial_score": initial_score,
        "initial_score_label": initial_score_label,
        "current_score": current_score,
        "current_score_label": current_score_label,
        "improvement": improvement,
        "trend": "improving" if (improvement or 0) > 0 else ("declining" if (improvement or 0) < 0 else "stable"),
        "current_streak": current_user.current_streak or 0,
        "longest_streak": current_user.longest_streak or 0,
        "total_checkins": current_user.total_checkins or 0,
        "checked_in_today": checked_in_today,
        "has_baseline": baseline_photo is not None,
        "category_labels": category_labels,
    }

    # ── Milestones ───────────────────────────────────────────────
    current_day_for_milestones = plan_info.get("current_day") if plan_info else 0
    completed_milestones = []
    next_milestone = None

    for day in MILESTONE_DAYS:
        m = MILESTONES[day]
        if current_day_for_milestones and current_day_for_milestones >= day:
            completed_milestones.append({
                "day": day,
                "label": m["title"],
                "emoji": m["emoji"],
                "achieved": True,
            })
        else:
            entry = {
                "day": day,
                "label": m["title"],
                "emoji": m["emoji"],
                "achieved": False,
                "days_until": day - (current_day_for_milestones or 0),
            }
            if next_milestone is None:
                next_milestone = entry

    milestones_info = {
        "next": next_milestone,
        "completed": completed_milestones,
        "total_milestones": len(MILESTONE_DAYS),
    }

    # ── Next action ──────────────────────────────────────────────
    next_action = _get_next_action(plan, current_user, db)

    return {
        "profile": profile,
        "plan": plan_info,
        "progress": progress_info,
        "milestones": milestones_info,
        "next_action": next_action,
    }


def _task_name(t) -> str:
    """Human-readable title for a task (plan tasks use {task}; older data {name})."""
    if isinstance(t, dict):
        title = t.get("task") or t.get("name") or t.get("title")
        if title:
            return str(title).strip()
        return "Daily task"
    return str(t).strip()


def _task_detail(t) -> str:
    """Optional detail/description for a task."""
    if isinstance(t, dict):
        detail = t.get("details") or t.get("description")
        if detail:
            return str(detail).strip()
    return ""


def _get_next_action(plan, user: User, db: Session) -> dict | None:
    """
    Determine what the user should do next based on their current plan state.
    """
    if not plan:
        return {
            "task": "Upload your first photo",
            "time": "Now",
            "description": "Take a clear front-facing photo in good lighting to get your baseline score and personalised 90-day plan.",
        }

    current_day = compute_current_day(plan)

    if current_day >= 90:
        return {
            "task": "🎉 Review your transformation",
            "time": "Now",
            "description": "Compare your Day 1 baseline with your Day 90 photo. Share your results!",
        }

    # Check if they've checked in today
    checked_in_today = (
        user.last_checkin_date is not None
        and user.last_checkin_date.date() == datetime.utcnow().date()
    )

    if not checked_in_today:
        # Find a morning task to suggest
        plan_data = plan.data or {}
        phases = plan_data.get("phases", plan.phases or {})

        current_phase_key = (
            "phase_1" if current_day <= 30 else ("phase_2" if current_day <= 60 else "phase_3")
        )
        current_week = ((current_day - 1) // 7) + 1 if current_day > 0 else 1

        phase_data = phases.get(current_phase_key, {})
        weekly_tasks = phase_data.get("weekly_tasks", [])
        current_week_tasks = None
        for week_data in weekly_tasks:
            if week_data.get("week") == current_week:
                current_week_tasks = week_data
                break

        if current_week_tasks and current_week_tasks.get("daily_tasks"):
            # Return the first morning task if available
            daily_tasks = current_week_tasks["daily_tasks"]
            am_tasks = [t for t in daily_tasks if isinstance(t, dict) and "am" in t.get("time", "").lower() or "morning" in str(t).lower()]
            if am_tasks:
                first = am_tasks[0]
                return {
                    "task": _task_name(first),
                    "time": "Morning",
                    "description": _task_detail(first),
                }
            first_task = daily_tasks[0]
            return {
                "task": _task_name(first_task),
                "time": "Today",
                "description": _task_detail(first_task),
            }

    # Fallback: remind about progress photo
    photo_checkpoints = [30, 60, 90]
    for day in photo_checkpoints:
        if abs(current_day - day) <= 3 and current_day < day:
            return {
                "task": f"Progress photo coming up (Day {day})",
                "time": "This week",
                "description": f"Prepare for your Day {day} progress photo to see visible changes.",
            }

    return {
        "task": "Complete today's daily tasks",
        "time": "Today",
        "description": f"Day {current_day}/90 — stay consistent to build lasting habits.",
    }