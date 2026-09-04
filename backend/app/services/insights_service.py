"""
Creative premium insights (Pro/Elite) — deterministic, gender-aware, zero-cost.

These are the "life-changing, out-of-the-box" extras that make Pro and Elite feel
worth paying for. Everything here is derived *locally* from an already-computed
score + category breakdown, so the endpoints stay fast, deterministic (unit-
testable), and never call DeepSeek/Redis or load torch/mediapipe.

  Pro   — Glow-Up Forecast, Percentile Rank, Look-Alike Archetype
  Elite — Golden-Ratio Harmony Map, Weekly Glow-Up Blueprint, Shareable Card
"""

from typing import Any, Dict, List, Optional

from app.services.score_calibration import compute_potential_score
from app.services.score_labels import get_score_label
from app.services.category_breakdown import normalize_breakdown


def gender_of(user_gender: Optional[str]) -> str:
    g = (user_gender or "other").strip().lower()
    return g if g in ("male", "female") else "other"


# ── Look-alike archetype (gender-aware, fun, shareable) ──────────────────────
# Names are vibe/archetype labels, not celebrity trademarks — safe to ship.
ARCHETYPES: Dict[str, Dict[str, tuple]] = {
    "male": {
        "oval": ("The Leading Man", "🎬"),
        "square": ("The Athlete", "🏆"),
        "heart": ("The Heartthrob", "💘"),
        "round": ("The Charmer", "😎"),
        "diamond": ("The Sharp One", "💎"),
        "long": ("The Strategist", "♟️"),
    },
    "female": {
        "oval": ("The Model", "💃"),
        "square": ("The Boss", "👑"),
        "heart": ("The Muse", "✨"),
        "round": ("The Sweetheart", "🌸"),
        "diamond": ("The Star", "🌟"),
        "long": ("The Icon", "🦋"),
    },
    "other": {
        "oval": ("The Muse", "✨"),
        "square": ("The Athlete", "🏆"),
        "heart": ("The Charmer", "😎"),
        "round": ("The Sweetheart", "🌸"),
        "diamond": ("The Star", "🌟"),
        "long": ("The Icon", "🦋"),
    },
}

CATEGORY_REASONS = {
    "facial_harmony": "balanced facial thirds",
    "skin_quality": "clear, even skin",
    "jawline_definition": "a defined jawline",
    "eye_appeal": "a strong eye area",
    "facial_structure": "sharp bone structure",
    "masculinity_femininity": "strong gender contrast",
    "symmetry": "high symmetry",
    "skin": "even skin tone",
    "jawline": "a defined jaw",
    "eyes": "expressive eyes",
}

SHAPE_NOTE = {
    "oval": "balanced oval proportions",
    "square": "a strong, defined jaw",
    "heart": "a distinctive, tapered chin",
    "round": "soft, youthful symmetry",
    "diamond": "high, defined cheekbones",
    "long": "a striking vertical proportion",
}


def _vibe(score: float) -> str:
    if score >= 80:
        return "Top-tier presence — you turn heads."
    if score >= 65:
        return "Strong, memorable features with real pull."
    if score >= 50:
        return "A solid foundation with serious upside."
    return "Raw potential — a glow-up waiting to happen."


def build_archetype(
    score: Optional[float],
    face_shape: Optional[str],
    gender: Optional[str],
    categories: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Map a score + face shape + category scores to a shareable archetype."""
    g = gender_of(gender)
    table = ARCHETYPES.get(g, ARCHETYPES["other"])
    shape = (face_shape or "oval").strip().lower()
    name, emoji = table.get(shape, table["oval"])

    categories = normalize_breakdown(categories)
    if categories:
        ranked = sorted(categories.items(), key=lambda kv: kv[1], reverse=True)
        reasons = [CATEGORY_REASONS.get(k, k.replace("_", " ")) for k, _ in ranked[:3]]
    else:
        reasons = [SHAPE_NOTE.get(shape, "balanced proportions")]

    return {
        "name": name,
        "emoji": emoji,
        "vibe": _vibe(float(score or 0)),
        "reasons": reasons,
    }


# ── Glow-up forecast (trajectory → Day 30/60/90) ────────────────────────────
def build_forecast(
    score: Optional[float],
    current_day: Optional[int],
    potential: Optional[float] = None,
) -> Dict[str, Any]:
    score = float(score or 0)
    if potential is None:
        potential = compute_potential_score(score) or score
    potential = float(potential)

    day = max(0, min(90, int(current_day or 0)))
    remaining = max(1, 90 - day)

    milestones = []
    for target in (30, 60, 90):
        if target <= day:
            projected = score
        else:
            progress = (target - day) / remaining
            projected = score + (potential - score) * progress
        milestones.append({"day": target, "projected_score": round(projected, 1)})

    label = get_score_label(potential)["label"]
    headline = f"You're tracking toward ~{round(potential, 1)} ({label}) by Day 90."

    return {
        "current_score": round(score, 1),
        "potential_score": round(potential, 1),
        "days_remaining": 90 - day,
        "headline": headline,
        "milestones": milestones,
    }


# ── Percentile rank ─────────────────────────────────────────────────────────
def rank_label(percentile: Optional[float]) -> str:
    if percentile is None:
        return "—"
    if percentile >= 99:
        return "Top 1%"
    if percentile >= 95:
        return "Top 5%"
    if percentile >= 90:
        return "Top 10%"
    if percentile >= 75:
        return "Top 25%"
    if percentile >= 50:
        return "Above average"
    return "Building fast"

# ── Golden-ratio harmony map (Elite) ────────────────────────────────────────
GOLDEN_METRICS = [
    ("facial_harmony", "Facial thirds & harmony"),
    ("facial_structure", "Bone structure"),
    ("jawline_definition", "Jawline angle"),
    ("eye_appeal", "Eye spacing & shape"),
    ("skin_quality", "Skin luminosity"),
    ("masculinity_femininity", "Gender contrast"),
]

GOLDEN_FALLBACK = [
    ("symmetry", "Symmetry"),
    ("skin", "Skin"),
    ("jawline", "Jawline"),
    ("eyes", "Eyes"),
]


def _harmony_summary(phi_score: Optional[float]) -> str:
    if phi_score is None:
        return "Analyze a photo to see your harmony map."
    if phi_score >= 80:
        return "Exceptional alignment with the golden ratio — your facial thirds are near-ideal."
    if phi_score >= 65:
        return "Strong harmony with one or two areas worth refining."
    if phi_score >= 50:
        return "Solid base — targeted work will measurably improve your balance."
    return "Clear structure — focused effort will noticeably raise your harmony."


def build_golden_ratio(
    categories: Optional[Dict[str, Any]],
    scores: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    categories = normalize_breakdown(categories)
    scores = scores if isinstance(scores, dict) else {}

    metrics: List[Dict[str, Any]] = []

    def add(key: str, label: str) -> None:
        raw = categories.get(key) if categories else scores.get(key)
        if raw is None:
            return
        value = round(float(raw), 1)
        metrics.append({"key": key, "label": label, "score": value, "alignment": value})

    for key, label in GOLDEN_METRICS:
        add(key, label)
    if not metrics:
        for key, label in GOLDEN_FALLBACK:
            add(key, label)

    phi_score = round(sum(m["score"] for m in metrics) / len(metrics), 1) if metrics else None
    return {"phi_score": phi_score, "summary": _harmony_summary(phi_score), "metrics": metrics}


# ── Weekly glow-up blueprint (Elite) ────────────────────────────────────────
FOCUS_LIBRARY = {
    "skin_quality": {"focus": "Skin", "task": "2-minute cleanse + moisturize (AM & PM).", "why": "Even skin lifts every other feature."},
    "skin": {"focus": "Skin", "task": "2-minute cleanse + moisturize (AM & PM).", "why": "Even skin lifts every other feature."},
    "jawline_definition": {"focus": "Jawline", "task": "2 minutes of tongue posture + jaw tension release.", "why": "A defined jawline sharpens your whole profile."},
    "jawline": {"focus": "Jawline", "task": "2 minutes of tongue posture + jaw tension release.", "why": "A defined jawline sharpens your whole profile."},
    "eye_appeal": {"focus": "Eyes", "task": "2 minutes of eye-area care + brow grooming.", "why": "The eye area is where people look first."},
    "eyes": {"focus": "Eyes", "task": "2 minutes of eye-area care + brow grooming.", "why": "The eye area is where people look first."},
    "facial_structure": {"focus": "Structure", "task": "Contrast grooming to sharpen bone structure (2 min).", "why": "Clean edges make bone structure read sharper."},
    "facial_harmony": {"focus": "Harmony", "task": "Balance facial thirds with a 2-minute symmetry routine.", "why": "Harmony is the single biggest driver of appeal."},
    "masculinity_femininity": {"focus": "Presence", "task": "2 minutes framing your strongest gender contrast.", "why": "Maximizing natural contrast reads as confidence."},
    "symmetry": {"focus": "Symmetry", "task": "2 minutes evening out grooming asymmetry.", "why": "Symmetry is processed as health at a glance."},
}

GENDER_NOTE = {
    "male": "This week's plan leans into masculine definition — jawline, symmetry and presence.",
    "female": "This week's plan leans into feminine balance — even skin, soft harmony and glow.",
    "other": "This week's plan focuses on balanced harmony and clear skin.",
}


def build_blueprint(weakest: Optional[List[str]], gender: Optional[str]) -> Dict[str, Any]:
    g = gender_of(gender)
    focuses: List[Dict[str, str]] = []
    for key in (weakest or [])[:3]:
        entry = FOCUS_LIBRARY.get(key)
        if entry and entry not in focuses:
            focuses.append(entry)

    defaults = [
        FOCUS_LIBRARY["skin_quality"],
        FOCUS_LIBRARY["facial_harmony"],
        FOCUS_LIBRARY["jawline_definition"],
    ]
    for default in defaults:
        if len(focuses) < 3 and default not in focuses:
            focuses.append(default)

    days = []
    for i in range(7):
        entry = focuses[i % len(focuses)]
        days.append(
            {
                "day": i + 1,
                "focus": entry["focus"],
                "task": entry["task"],
                "why": entry["why"],
                "duration_minutes": 2,
            }
        )

    return {
        "week_label": "This week's glow-up",
        "gender_note": GENDER_NOTE.get(g, GENDER_NOTE["other"]),
        "days": days,
    }


# ── Shareable glow-up card (Elite) ──────────────────────────────────────────
def build_glow_up_card(
    name: Optional[str],
    score: Optional[float],
    score_label: Optional[str],
    archetype_name: str,
    top_strength: str,
    current_day: Optional[int],
    tier: Optional[str],
) -> Dict[str, Any]:
    score = float(score or 0)
    label = score_label or str(get_score_label(score)["label"])
    day = int(current_day or 0)
    return {
        "headline": f"{name or 'Your'}'s Glow-Up",
        "score": round(score, 1),
        "label": label,
        "archetype": archetype_name,
        "top_strength": top_strength,
        "day": day,
        "tier": (tier or "pro").lower(),
        "share_text": (
            f"I scored {round(score, 1)}/100 on LookMaxx ({label}) — "
            f"{archetype_name} energy. Day {day}/90."
        ),
    }

