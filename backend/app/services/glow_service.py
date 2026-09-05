"""
Glow — daily variable-reward reveal (deterministic-first, zero AI, zero infra).

Implements gambling's six mechanisms rewired to genuine happiness (§2 of the
Momentum spec). Every reward is TRUE (your own score, streak, photos, archetype);
the only randomness is *which* genuine reward you get. Random picks use the
stdlib `secrets` module — no torch/mediapipe/DeepSeek/Redis in the daily loop.
"""

import secrets
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.models import GlowReveal, GlowState, Photo, Plan, User
from app.services.category_breakdown import normalize_breakdown
from app.services.insights_service import build_archetype
from app.services.progress_engine import compute_current_day
from app.services.score_calibration import compute_potential_score
from app.services.score_labels import get_score_label

# Rarity weights (sum to 100). Pro/Elite get richer reveals (§4).
WEIGHTS = {
    "free": {"common": 70, "rare": 24, "epic": 5, "legendary": 1},
    "pro": {"common": 60, "rare": 25, "epic": 10, "legendary": 5},
    "elite": {"common": 60, "rare": 25, "epic": 10, "legendary": 5},
}

MAX_BLUR = 24


def blur_for_day(day: int) -> int:
    """Blur→sharp formula: Day 1 = 24px (silhouette), Day 90 = 0px (full)."""
    d = max(1, min(90, int(day or 1)))
    return max(0, min(MAX_BLUR, MAX_BLUR - round(d * MAX_BLUR / 90)))


def journey_day(user: User, db: Session) -> int:
    """The user's plan day (1..90); falls back to 1 when there is no plan yet."""
    plan = (
        db.query(Plan)
        .filter(Plan.user_id == user.id, Plan.is_active == True)  # noqa: E712
        .order_by(Plan.created_at.desc())
        .first()
    )
    return compute_current_day(plan) if plan else 1


def _tier(user: User) -> str:
    t = (user.subscription_tier or "free").lower()
    return t if t in WEIGHTS else "free"


def _get_state(user: User, db: Session) -> GlowState:
    state = db.query(GlowState).filter(GlowState.user_id == user.id).first()
    if state is None:
        state = GlowState(
            user_id=user.id, glow_streak=0, longest_glow_streak=0,
            opens_count=0, consecutive_commons=0, milestone_flags={},
        )
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def _latest_photo(user: User, db: Session) -> Optional[Photo]:
    return (
        db.query(Photo)
        .filter(Photo.user_id == user.id, Photo.score.isnot(None))
        .order_by(Photo.captured_at.desc())
        .first()
    )


def _baseline_photo(user: User, db: Session) -> Optional[Photo]:
    return (
        db.query(Photo)
        .filter(Photo.user_id == user.id, Photo.score.isnot(None))
        .order_by(Photo.captured_at.asc())
        .first()
    )


def _archetype_name(user: User, db: Session) -> Optional[str]:
    photo = _latest_photo(user, db)
    if photo is None:
        return None
    details = photo.analysis_details if isinstance(photo.analysis_details, dict) else {}
    breakdown = normalize_breakdown(details.get("category_breakdown"))
    return build_archetype(photo.score, photo.face_shape, user.gender, breakdown).get("name")


TIPS = [
    "Give two focused minutes to your weakest feature today.",
    "Drink water before your first screen — skin starts hydrated.",
    "Hold good posture for five minutes — jaw and neck follow.",
    "Do one quick grooming pass: brows, beard line, or skincare.",
]

UNLOCKS = [
    {"item_type": "mini_lesson", "emoji": "📚", "title": "Mini-lesson unlocked",
     "body": "Symmetry reads as health. One small, even grooming choice daily moves the needle."},
    {"item_type": "badge_preview", "emoji": "🏅", "title": "A title is forming",
     "body": "Keep your streak alive and a title will claim itself."},
    {"item_type": "affiliate_spotlight", "emoji": "🛒", "title": "A real tool, spotlighted",
     "body": "Your plan already names the product categories that match your weakest areas."},
]


def _build_micro_win(user: User, state: GlowState, journey: int, db: Session) -> Dict[str, Any]:
    options: list = []
    photo = _latest_photo(user, db)
    if photo and photo.score is not None:
        potential = compute_potential_score(photo.score)
        if potential:
            options.append({
                "kind": "potential", "emoji": "📈",
                "headline": f"You're {round(photo.score / potential * 100)}% of the way to your potential",
                "body": f"Your potential score is {potential:.0f}. Small daily wins close the gap.",
            })
        label = get_score_label(photo.score)["label"]
        options.append({
            "kind": "label", "emoji": "🏷️",
            "headline": f"You're in the '{label}' tier",
            "body": f"Score {photo.score:.0f} sits in the {label} range — and it's still climbing.",
        })
    if (state.glow_streak or 0) >= 2:
        options.append({
            "kind": "streak", "emoji": "🔥",
            "headline": f"Day {state.glow_streak} of your Glow streak",
            "body": "Every day you show up, your future face comes into focus.",
        })
    options.append({
        "kind": "tip", "emoji": "⏱️",
        "headline": "A two-minute win",
        "body": TIPS[secrets.randbelow(len(TIPS))],
    })
    return options[secrets.randbelow(len(options))]


def _build_glimpse(user: User, journey: int, db: Session, gold: bool = False) -> Optional[Dict[str, Any]]:
    photo = _latest_photo(user, db)
    if photo is None:
        return None
    blur = 0 if gold else blur_for_day(journey)
    if gold:
        return {
            "kind": "gold_glow", "emoji": "✨",
            "photo_url": photo.file_url, "blur_px": blur,
            "headline": "Gold Glow — this is yours",
            "body": "A sharper glimpse of your future self. Show up tomorrow to see it clearer still.",
            "share_text": f"I'm {journey} days into my glow-up. Score {photo.score:.0f} and climbing.",
        }
    return {
        "kind": "glimpse", "emoji": "👁️",
        "photo_url": photo.file_url, "blur_px": blur,
        "headline": "This is you — sharper every day",
        "body": f"Day {journey}/90. Come back tomorrow to see yourself come into focus.",
        "share_text": None,
    }


def _build_unlock(archetype_name: Optional[str]) -> Dict[str, Any]:
    unlock = dict(UNLOCKS[secrets.randbelow(len(UNLOCKS))])
    if unlock["item_type"] == "badge_preview" and archetype_name:
        unlock["body"] = f"Your '{archetype_name}' title is forming. Keep showing up to claim it."
    return unlock


def _build_full_reveal(user: User, db: Session) -> Optional[Dict[str, Any]]:
    baseline = _baseline_photo(user, db)
    latest = _latest_photo(user, db)
    if baseline is None or latest is None:
        return None
    before = baseline.score or 0
    after = latest.score or 0
    delta = round(after - before, 1)
    return {
        "kind": "full_reveal", "emoji": "🏆",
        "before_url": baseline.file_url, "after_url": latest.file_url,
        "before_score": round(before, 1), "after_score": round(after, 1),
        "delta": delta, "blur_px": 0,
        "headline": "Day 90 — proof you changed",
        "body": f"You moved {delta:+.1f} points. This is your transformation, no filter.",
        "share_text": f"I went from {before:.0f} to {after:.0f} in 90 days. #LookMaxxGlowUp",
    }


def _roll_rarity(tier: str) -> str:
    weights = WEIGHTS.get(tier, WEIGHTS["free"])
    roll = secrets.randbelow(100)
    acc = 0
    for rarity in ("common", "rare", "epic", "legendary"):
        acc += weights[rarity]
        if roll < acc:
            return rarity
    return "common"


def _decide_rarity(tier: str, state: GlowState, journey: int, flags: Dict[str, Any],
                   opens_before: int, consecutive_commons: int) -> str:
    """Streak jackpots → first-open hook → pity timer → weighted roll."""
    if journey >= 90:
        return "legendary"
    streak = state.glow_streak or 0
    if streak == 30 and not flags.get("streak30_claimed"):
        return "epic"
    if streak == 7 and not flags.get("streak7_claimed"):
        return "rare"
    if opens_before == 0 and tier == "free":
        return "rare"
    if consecutive_commons >= 2:
        return "rare"
    return _roll_rarity(tier)


def _build_reward(user: User, db: Session, state: GlowState, journey: int, tier: str,
                  opens_before: int, consecutive_before: int) -> Tuple[str, str, Dict[str, Any]]:
    flags = state.milestone_flags or {}
    rarity = _decide_rarity(tier, state, journey, flags, opens_before, consecutive_before)
    archetype_name = _archetype_name(user, db)

    if journey >= 90 or rarity == "legendary":
        if journey >= 90 and tier == "elite":
            payload = _build_full_reveal(user, db)
            if payload:
                return "legendary", "full_reveal", payload
        payload = _build_glimpse(user, journey, db, gold=True)
        if payload is None:
            return rarity, "micro_win", _build_micro_win(user, state, journey, db)
        return "legendary", "gold_glow", payload

    if rarity == "rare":
        payload = _build_glimpse(user, journey, db)
        if payload is None:
            return rarity, "micro_win", _build_micro_win(user, state, journey, db)
        return "rare", "glimpse", payload

    if rarity == "epic":
        return "epic", "unlock", _build_unlock(archetype_name)

    return "common", "micro_win", _build_micro_win(user, state, journey, db)


def _reveal_dict(reveal: GlowReveal) -> Dict[str, Any]:
    return {
        "id": reveal.id,
        "day": reveal.journey_day,
        "rarity": reveal.rarity,
        "reward_type": reveal.reward_type,
        "payload": reveal.payload or {},
        "opened_at": reveal.opened_at.isoformat() if reveal.opened_at else None,
    }


def _state_dict(state: GlowState, journey: int, tier: str) -> Dict[str, Any]:
    return {
        "journey_day": journey,
        "glow_streak": state.glow_streak or 0,
        "longest_glow_streak": state.longest_glow_streak or 0,
        "opens_count": state.opens_count or 0,
        "blur_next": blur_for_day(journey),
        "full_reveal": {"eligible": journey >= 90, "unlocked": tier == "elite"},
        "weights": WEIGHTS.get(tier, WEIGHTS["free"]),
    }


def get_glow_state(user: User, db: Session) -> Dict[str, Any]:
    journey = journey_day(user, db)
    state = _get_state(user, db)
    tier = _tier(user)
    today = datetime.utcnow().date()
    existing = (
        db.query(GlowReveal)
        .filter(GlowReveal.user_id == user.id, GlowReveal.open_date == today)
        .first()
    )
    return {
        "can_open": existing is None,
        "opened_today": existing is not None,
        "today_reveal": _reveal_dict(existing) if existing else None,
        "state": _state_dict(state, journey, tier),
    }


def open_today(user: User, db: Session) -> Dict[str, Any]:
    tier = _tier(user)
    journey = journey_day(user, db)
    today = datetime.utcnow().date()

    existing = (
        db.query(GlowReveal)
        .filter(GlowReveal.user_id == user.id, GlowReveal.open_date == today)
        .first()
    )
    if existing:
        return {
            "already_opened": True,
            "reveal": _reveal_dict(existing),
            "state": _state_dict(_get_state(user, db), journey, tier),
        }

    state = _get_state(user, db)

    yesterday = today - timedelta(days=1)
    if state.last_open_date == today:
        pass  # unreachable due to idempotency check, guarded anyway
    elif state.last_open_date == yesterday:
        state.glow_streak = (state.glow_streak or 0) + 1
    else:
        state.glow_streak = 1
    state.longest_glow_streak = max(state.longest_glow_streak or 0, state.glow_streak)

    opens_before = state.opens_count or 0
    consecutive_before = state.consecutive_commons or 0
    flags = state.milestone_flags or {}

    rarity, reward_type, payload = _build_reward(
        user, db, state, journey, tier, opens_before, consecutive_before)

    if rarity == "common":
        state.consecutive_commons = consecutive_before + 1
    else:
        state.consecutive_commons = 0

    if rarity == "rare" and (state.glow_streak or 0) == 7:
        flags["streak7_claimed"] = True
    if rarity == "epic" and (state.glow_streak or 0) == 30:
        flags["streak30_claimed"] = True
    if journey >= 90:
        flags["day90_claimed"] = True

    state.milestone_flags = flags
    state.opens_count = opens_before + 1
    state.last_open_date = today

    reveal = GlowReveal(
        user_id=user.id, open_date=today, journey_day=journey,
        rarity=rarity, reward_type=reward_type, payload=payload,
    )
    db.add(reveal)
    db.commit()
    db.refresh(reveal)
    db.refresh(state)

    return {
        "already_opened": False,
        "reveal": _reveal_dict(reveal),
        "state": _state_dict(state, journey, tier),
    }


def get_reveals(user: User, db: Session, limit: int = 30) -> Dict[str, Any]:
    reveals = (
        db.query(GlowReveal)
        .filter(GlowReveal.user_id == user.id)
        .order_by(GlowReveal.opened_at.desc())
        .limit(limit)
        .all()
    )
    return {"reveals": [_reveal_dict(r) for r in reveals], "total": len(reveals)}


def get_full_reveal(user: User, db: Session) -> Optional[Dict[str, Any]]:
    return _build_full_reveal(user, db)



