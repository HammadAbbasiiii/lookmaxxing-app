"""
The Arc — RPG XP / levels / quests / badges (deterministic, zero AI, zero infra).

Every XP point traces to a *real, server-verified* action (a check-in, a quest
completed inside a check-in, a re-score, a plan task, a streak milestone). Nothing
is awarded for opening the app. Levels are derived from XP — never trusted from
the client. Badges are insert-or-ignore against a ``(user_id, badge_key)`` unique
pair, so re-awarding is a no-op.
"""

import math
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models import ArcState, Photo, Plan, User, UserBadge, UserCheckin, generate_uuid
from app.services.category_breakdown import normalize_breakdown
from app.services.insights_service import FOCUS_LIBRARY, build_archetype
from app.services.progress_engine import compute_current_day

XP = {
    "checkin": 50,
    "quest": 100,
    "rescore": 200,
    "plan_task": 20,
    "streak_milestone": 150,
}

STREAK_MILESTONES = [7, 14, 21, 30, 45, 60, 75, 90]
PLAN_MILESTONES = [7, 14, 21, 30, 45, 60, 75, 90]

BADGE_CATALOG = {
    "first_score": {"name": "First Glow", "emoji": "✨", "description": "Your first scored photo."},
    "day7": {"name": "Week One", "emoji": "🌱", "description": "Seven days on the plan."},
    "day14": {"name": "Two Weeks In", "emoji": "🌿", "description": "Two weeks of showing up."},
    "day21": {"name": "Habit Formed", "emoji": "🔁", "description": "Three weeks — it's a habit now."},
    "day30": {"name": "Unstoppable", "emoji": "⚡", "description": "Thirty days, no plan left behind."},
    "day45": {"name": "Halfway", "emoji": "⛰️", "description": "You're halfway to Day 90."},
    "day60": {"name": "Unshakeable", "emoji": "🛡️", "description": "Sixty days of momentum."},
    "day75": {"name": "Final Stretch", "emoji": "🏁", "description": "The last 15 days."},
    "day90": {"name": "Transformed", "emoji": "🏆", "description": "You finished the full plan."},
    "streak7": {"name": "Disciplined", "emoji": "🔥", "description": "A 7-day check-in streak."},
    "streak30": {"name": "Ironclad", "emoji": "💎", "description": "A 30-day check-in streak."},
}


def level_for_xp(total_xp: int) -> int:
    """Deterministic curve: level = floor(sqrt(xp / 100)) + 1."""
    return int(math.floor(math.sqrt(max(0, int(total_xp or 0)) / 100.0))) + 1


def xp_to_next_level(total_xp: int) -> int:
    level = level_for_xp(total_xp)
    threshold = (level ** 2) * 100
    return max(0, threshold - int(total_xp or 0))


def title_for(archetype_name: Optional[str], level: int) -> str:
    return f"The {archetype_name or 'Rookie'}, Level {level}"


def milestone_title_for(user: User, plan_day: int) -> Optional[str]:
    if plan_day >= 90:
        return "Transformed"
    streak = user.current_streak or 0
    if streak >= 30:
        return "Unstoppable"
    if streak >= 7:
        return "Disciplined"
    return None


def _get_state(user: User, db: Session) -> ArcState:
    state = db.query(ArcState).filter(ArcState.user_id == user.id).first()
    if state is None:
        state = ArcState(user_id=user.id, total_xp=0, current_level=1,
                         quests=[], xp_events={})
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def _latest_scored_photo(user: User, db: Session) -> Optional[Photo]:
    return (
        db.query(Photo)
        .filter(Photo.user_id == user.id, Photo.score.isnot(None))
        .order_by(Photo.captured_at.desc())
        .first()
    )


def _archetype_name(user: User, db: Session) -> Optional[str]:
    photo = _latest_scored_photo(user, db)
    if photo is None:
        return None
    details = photo.analysis_details if isinstance(photo.analysis_details, dict) else {}
    breakdown = normalize_breakdown(details.get("category_breakdown"))
    return build_archetype(photo.score, photo.face_shape, user.gender, breakdown).get("name")


def _weakest_features(user: User, db: Session) -> List[str]:
    photo = _latest_scored_photo(user, db)
    if photo is None:
        return []
    details = photo.analysis_details if isinstance(photo.analysis_details, dict) else {}
    breakdown = normalize_breakdown(details.get("category_breakdown"))
    return sorted(breakdown, key=lambda k: breakdown.get(k, 0))[:3]


def _plan_day(user: User, db: Session) -> int:
    plan = (
        db.query(Plan)
        .filter(Plan.user_id == user.id, Plan.is_active == True)  # noqa: E712
        .order_by(Plan.created_at.desc())
        .first()
    )
    return compute_current_day(plan) if plan else 1


def generate_quests(user: User, db: Session) -> List[Dict[str, Any]]:
    """1–3 daily quests, targeted at the user's weakest features."""
    weakest = _weakest_features(user, db)
    focuses: List[Dict[str, str]] = []
    for key in weakest:
        entry = FOCUS_LIBRARY.get(key)
        if entry and entry not in focuses:
            focuses.append(entry)
    defaults = [
        FOCUS_LIBRARY["skin_quality"],
        FOCUS_LIBRARY["facial_harmony"],
        FOCUS_LIBRARY["jawline_definition"],
    ]
    for d in defaults:
        if len(focuses) < 3 and d not in focuses:
            focuses.append(d)

    quests = []
    for entry in focuses[:3]:
        quests.append({
            "id": generate_uuid(),
            "focus": entry["focus"],
            "task": entry["task"],
            "why": entry["why"],
            "xp": XP["quest"],
            "claimed": False,
        })
    return quests


def _award(state: ArcState, events: Dict[str, Any], key: str, amount: int) -> bool:
    """Append XP to the ledger if this event hasn't been counted yet."""
    if key in events:
        return False
    events[key] = amount
    state.total_xp = (state.total_xp or 0) + amount
    return True


def sync_xp(user: User, state: ArcState, db: Session) -> None:
    """Award XP for real, server-verified actions (idempotent via xp_events)."""
    events = dict(state.xp_events) if isinstance(state.xp_events, dict) else {}
    changed = False

    checkins = (
        db.query(UserCheckin)
        .filter(UserCheckin.user_id == user.id)
        .order_by(UserCheckin.created_at.asc())
        .all()
    )
    for checkin in checkins:
        if _award(state, events, f"checkin:{checkin.id}", XP["checkin"]):
            changed = True
        tasks = checkin.completed_tasks if isinstance(checkin.completed_tasks, list) else []
        for i, _task in enumerate(tasks[:3]):
            if _award(state, events, f"task:{checkin.id}:{i}", XP["plan_task"]):
                changed = True

    photos = (
        db.query(Photo)
        .filter(Photo.user_id == user.id, Photo.score.isnot(None))
        .order_by(Photo.captured_at.asc())
        .all()
    )
    for i, photo in enumerate(photos):
        if i == 0:
            continue  # the baseline is not a "re-score"
        if _award(state, events, f"rescore:{photo.id}", XP["rescore"]):
            changed = True

    longest = user.longest_streak or user.current_streak or 0
    for milestone in STREAK_MILESTONES:
        if longest >= milestone and _award(state, events, f"streak:{milestone}", XP["streak_milestone"]):
            changed = True

    if changed:
        state.xp_events = events
        state.current_level = level_for_xp(state.total_xp)
        db.commit()
        db.refresh(state)


def sync_badges(user: User, state: ArcState, db: Session) -> None:
    """Award any earned-but-unclaimed badges (insert-or-ignore semantics)."""
    existing = {
        b.badge_key for b in db.query(UserBadge).filter(UserBadge.user_id == user.id).all()
    }
    earned = []
    if _latest_scored_photo(user, db) is not None:
        earned.append("first_score")
    plan_day = _plan_day(user, db)
    for day in PLAN_MILESTONES:
        if plan_day >= day:
            earned.append(f"day{day}")
    streak = user.longest_streak or user.current_streak or 0
    if streak >= 7:
        earned.append("streak7")
    if streak >= 30:
        earned.append("streak30")

    for key in earned:
        if key in existing or key not in BADGE_CATALOG:
            continue
        db.add(UserBadge(user_id=user.id, badge_key=key))
    db.commit()


def _quest_dict(q: Dict[str, Any], locked: bool) -> Dict[str, Any]:
    return {
        "id": q["id"],
        "focus": q.get("focus"),
        "task": q.get("task"),
        "why": q.get("why"),
        "xp": q.get("xp"),
        "claimed": bool(q.get("claimed")),
        "locked": locked,
    }


def _badge_dict(badge: UserBadge) -> Dict[str, Any]:
    meta = BADGE_CATALOG.get(badge.badge_key, {})
    return {
        "badge_key": badge.badge_key,
        "name": meta.get("name", badge.badge_key),
        "emoji": meta.get("emoji", "🏅"),
        "description": meta.get("description", ""),
        "unlocked_at": badge.awarded_at.isoformat() if badge.awarded_at else None,
    }


def get_state(user: User, db: Session, premium: bool) -> Dict[str, Any]:
    state = _get_state(user, db)
    today = datetime.utcnow().date()

    if state.quest_date != today or not isinstance(state.quests, list):
        state.quest_date = today
        state.quests = generate_quests(user, db)
        db.commit()
        db.refresh(state)

    sync_xp(user, state, db)
    sync_badges(user, state, db)

    archetype_name = _archetype_name(user, db)
    level = level_for_xp(state.total_xp)
    plan_day = _plan_day(user, db)

    badges = (
        db.query(UserBadge)
        .filter(UserBadge.user_id == user.id)
        .order_by(UserBadge.awarded_at.asc())
        .all()
    )

    quests = [_quest_dict(q, locked=not premium) for q in state.quests]

    tree_nodes = []
    for day in PLAN_MILESTONES:
        tree_nodes.append({
            "key": f"day{day}",
            "name": BADGE_CATALOG[f"day{day}"]["name"],
            "emoji": BADGE_CATALOG[f"day{day}"]["emoji"],
            "unlocked": plan_day >= day,
        })
    for feat in ("first_score", "streak7", "streak30"):
        tree_nodes.append({
            "key": feat,
            "name": BADGE_CATALOG[feat]["name"],
            "emoji": BADGE_CATALOG[feat]["emoji"],
            "unlocked": any(b.badge_key == feat for b in badges),
        })

    return {
        "level": level,
        "total_xp": state.total_xp or 0,
        "xp_to_next": xp_to_next_level(state.total_xp),
        "title": title_for(archetype_name, level),
        "archetype": archetype_name or "Rookie",
        "milestone_title": milestone_title_for(user, plan_day),
        "premium": premium,
        "today_quests": quests,
        "badges": [_badge_dict(b) for b in badges],
        "skill_tree": tree_nodes,
    }


def claim_quest(user: User, db: Session, quest_id: str) -> Dict[str, Any]:
    state = _get_state(user, db)
    today = datetime.utcnow().date()

    if state.quest_date != today or not isinstance(state.quests, list):
        state.quest_date = today
        state.quests = generate_quests(user, db)
        db.commit()
        db.refresh(state)

    quest = next((q for q in state.quests if q.get("id") == quest_id), None)
    if quest is None:
        return {"error": "quest_not_found"}

    if quest.get("claimed"):
        return {"error": "already_claimed"}

    # The quest must be backed by a real, server-verified check-in today whose
    # completed_tasks contains the quest task. No check-in → no XP (no farming).
    today_checkin = (
        db.query(UserCheckin)
        .filter(UserCheckin.user_id == user.id)
        .order_by(UserCheckin.created_at.desc())
        .first()
    )
    if today_checkin is None:
        return {"error": "not_done"}

    checkin_day = today_checkin.created_at.date() if today_checkin.created_at else None
    if checkin_day != today:
        return {"error": "not_done"}

    tasks = today_checkin.completed_tasks if isinstance(today_checkin.completed_tasks, list) else []
    if quest.get("task") not in tasks:
        return {"error": "not_done"}

    events = dict(state.xp_events) if isinstance(state.xp_events, dict) else {}
    _award(state, events, f"quest:{quest_id}", quest.get("xp", XP["quest"]))
    state.xp_events = events

    quest["claimed"] = True
    state.quests = [q if q.get("id") != quest_id else quest for q in state.quests]
    flag_modified(state, "quests")

    old_level = state.current_level or 1
    state.total_xp = state.total_xp or 0
    new_level = level_for_xp(state.total_xp)
    state.current_level = new_level
    db.commit()
    db.refresh(state)

    sync_badges(user, state, db)

    leveled_up = new_level > old_level
    archetype_name = _archetype_name(user, db)
    return {
        "xp_awarded": quest.get("xp", XP["quest"]),
        "level": new_level,
        "total_xp": state.total_xp,
        "leveled_up": leveled_up,
        "new_title": title_for(archetype_name, new_level) if leveled_up else None,
    }


def get_badges(user: User, db: Session) -> List[Dict[str, Any]]:
    badges = (
        db.query(UserBadge)
        .filter(UserBadge.user_id == user.id)
        .order_by(UserBadge.awarded_at.asc())
        .all()
    )
    return [_badge_dict(b) for b in badges]



