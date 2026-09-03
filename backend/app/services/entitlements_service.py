"""
Server-authoritative entitlement service (§5.2 — the browser is untrusted).

The single source of truth for what each tier gets. `/entitlements` exposes it
to the client purely for UX (lock chips, teasers, "upgrade" nudges); every
premium endpoint still calls `require_pro`/`require_elite` independently, so no
amount of client fiddling can unlock real data.

`enforce_*` helpers are called at the start of the photo/analysis paths so the
expensive face-detection + DeepSeek work never runs for a user who shouldn't be
paying for it.
"""

from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Photo, User

# The premium feature matrix. `tier` is the minimum tier that unlocks the feature.
# `teaser` is the curiosity hook shown to users who haven't unlocked it yet.
FEATURES: List[Dict[str, Any]] = [
    {
        "key": "unlimited_analyses",
        "name": "Unlimited analyses",
        "description": "Re-score as often as you want — track every week, not just once.",
        "teaser": "Free tier includes 1 analysis. See how you change week to week.",
        "tier": "pro",
    },
    {
        "key": "full_report",
        "name": "Full AI report",
        "description": "A written, coach-grade breakdown of your strengths and the exact fix for each weak area.",
        "teaser": "See your top 3 fixes and the routine that gets you there.",
        "tier": "pro",
    },
    {
        "key": "ai_coach",
        "name": "Daily AI coach",
        "description": "One personalized tip every day, based on your score and goals.",
        "teaser": "Tomorrow's tip is ready — unlock to read it.",
        "tier": "pro",
    },
    {
        "key": "plan",
        "name": "90-day plan + check-ins",
        "description": "Your full day-by-day plan with daily check-ins and milestone tracking.",
        "teaser": "Stay on track with a plan built around your weakest areas.",
        "tier": "pro",
    },
    {
        "key": "before_after",
        "name": "Before / after comparison",
        "description": "Drag-to-reveal baseline vs. latest photo to see real progress.",
        "teaser": "Your Day 30 comparison is waiting.",
        "tier": "pro",
    },
    {
        "key": "priority_coach",
        "name": "1:1 coach Q&A",
        "description": "Ask a real coach a question and get a personal answer within 24h.",
        "teaser": "Stuck on a routine? Get a human answer.",
        "tier": "elite",
    },
    {
        "key": "glow_up_forecast",
        "name": "Glow-Up Forecast",
        "description": "Your projected score at Day 30, 60 and 90 — and the tier you're tracking toward.",
        "teaser": "You're on track for a top-tier score by Day 90.",
        "tier": "pro",
    },
    {
        "key": "percentile_rank",
        "name": "Percentile Rank",
        "description": "Where your score stands against others like you — and the rank you can claim.",
        "teaser": "See how your score ranks against everyone else.",
        "tier": "pro",
    },
    {
        "key": "archetype_match",
        "name": "Look-Alike Archetype",
        "description": "The celebrity-grade vibe your face projects — fun, gender-aware and shareable.",
        "teaser": "Which archetype do you look like? Find out.",
        "tier": "pro",
    },
    {
        "key": "golden_ratio",
        "name": "Golden-Ratio Harmony Map",
        "description": "Your face measured against phi (1.618): thirds, symmetry, jawline, eyes and skin.",
        "teaser": "See exactly how your face measures against the golden ratio.",
        "tier": "elite",
    },
    {
        "key": "weekly_blueprint",
        "name": "Weekly Glow-Up Blueprint",
        "description": "A day-by-day 7-day plan built around your weakest areas — the deep version of your daily coach.",
        "teaser": "Your next 7 days, planned day by day.",
        "tier": "elite",
    },
    {
        "key": "glow_up_card",
        "name": "Shareable Glow-Up Card",
        "description": "A stylized score card with your archetype and rank — built to screenshot and share.",
        "teaser": "Show off your score with a share-ready card.",
        "tier": "elite",
    },
]

TIER_RANK = {"free": 0, "pro": 1, "elite": 2}


def get_tier(user: User) -> str:
    tier = (user.subscription_tier or "free").lower()
    return tier if tier in TIER_RANK else "free"


def is_premium(user: User) -> bool:
    return get_tier(user) in ("pro", "elite")


def count_analyses(user: User, db: Session) -> int:
    """Number of photos that have already been scored for this user."""
    return (
        db.query(Photo)
        .filter(Photo.user_id == user.id, Photo.score.isnot(None))
        .count()
    )


def count_photos(user: User, db: Session) -> int:
    return db.query(Photo).filter(Photo.user_id == user.id).count()


def get_entitlements(user: User, db: Session) -> Dict[str, Any]:
    tier = get_tier(user)
    analyses = count_analyses(user, db)
    photos = count_photos(user, db)
    unlimited = tier in ("pro", "elite")
    allowed: Optional[int] = None if unlimited else settings.FREE_ANALYSIS_LIMIT

    features = []
    for f in FEATURES:
        unlocked = TIER_RANK.get(tier, 0) >= TIER_RANK.get(f["tier"], 1)
        features.append(
            {
                "key": f["key"],
                "name": f["name"],
                "description": f["description"],
                "teaser": f["teaser"],
                "tier": f["tier"],
                "locked": not unlocked,
            }
        )

    return {
        "tier": tier,
        "is_subscribed": tier in ("pro", "elite"),
        "subscription_end": user.subscription_end.isoformat() if user.subscription_end else None,
        "limits": {
            "analyses": {
                "used": analyses,
                "allowed": allowed,
                "unlimited": unlimited,
                "remaining": None if unlimited else max(0, (allowed or 0) - analyses),
            },
            "photos": photos,
        },
        "features": features,
    }


def enforce_analysis_limit(user: User, db: Session, exclude_photo_id: Optional[str] = None) -> None:
    """Raise 403 if a free user has already used their analysis allowance."""
    if is_premium(user):
        return

    q = db.query(Photo).filter(Photo.user_id == user.id, Photo.score.isnot(None))
    if exclude_photo_id:
        q = q.filter(Photo.id != exclude_photo_id)
    used = q.count()

    if used >= settings.FREE_ANALYSIS_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "upgrade_required",
                "message": "You've used your free analysis. Upgrade to Pro for unlimited analyses.",
            },
        )


def enforce_photo_limit(user: User, db: Session) -> None:
    """Block free users from piling up un-analysed photos (storage + spam guard)."""
    if is_premium(user):
        return
    if count_photos(user, db) >= settings.FREE_ANALYSIS_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "upgrade_required",
                "message": "You've reached the free upload limit. Upgrade to Pro for unlimited analyses.",
            },
        )
