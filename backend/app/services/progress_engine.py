"""
Shared progress / streak engine.

Single source of truth for two rules that were previously scattered (and buggy)
across the plan and progress routes:

1. ``current_day`` is CALENDAR-based — Day 1 is the day the plan was created and
   it advances by exactly one per real day (capped at 90). A user can never
   "click through" the 90 days, because the day number is derived from wall-clock
   time, not from how many times they hit the check-in endpoint.

2. A user can only check in ONCE per calendar day. Repeated check-ins on the same
   day must be rejected by the routes so streaks and day counts can't be farmed
   in a few minutes.
"""

from datetime import datetime

from app.models import User


def compute_current_day(plan) -> int:
    """
    Return the calendar-correct current day (1..90) for a plan.

    Day 1 == the day the plan was created. Tomorrow is Day 2, and so on, capped
    at 90. This makes "day skipping" impossible: the number follows real time.
    """
    if plan is not None and getattr(plan, "created_at", None) is not None:
        days_elapsed = (datetime.utcnow().date() - plan.created_at.date()).days
        return max(1, min(days_elapsed + 1, 90))
    return 1


def compute_current_week(day: int) -> int:
    """Derive the 1-based week number (each week = 7 days) from a day number."""
    return max(1, ((max(1, day) - 1) // 7) + 1)


def update_streak(user: User) -> dict:
    """
    Update streak counters after a check-in. Returns streak state.

    - Same calendar day            -> no change (idempotent).
    - Consecutive day              -> extend streak.
    - Gap of more than one day     -> reset streak to 1.
    - First ever check-in          -> start at 1.
    """
    today = datetime.utcnow().date()
    last_checkin = user.last_checkin_date.date() if user.last_checkin_date else None

    if last_checkin == today:
        return {
            "streak_updated": False,
            "current_streak": user.current_streak or 0,
            "longest_streak": user.longest_streak or 0,
        }

    if last_checkin and (today - last_checkin).days == 1:
        user.current_streak = (user.current_streak or 0) + 1
    elif last_checkin and (today - last_checkin).days > 1:
        user.current_streak = 1
    else:
        user.current_streak = 1

    if (user.current_streak or 0) > (user.longest_streak or 0):
        user.longest_streak = user.current_streak

    user.total_checkins = (user.total_checkins or 0) + 1
    user.last_checkin_date = datetime.utcnow()

    return {
        "streak_updated": True,
        "current_streak": user.current_streak,
        "longest_streak": user.longest_streak,
    }
