"""Normalize a category breakdown into a flat ``{category: score}`` dict.

The analysis pipeline stores ``category_breakdown`` as a *nested* dict in the
current production path (see ``face_analysis_service.get_category_breakdown``):

    {
        "facial_harmony": {"score": 78.2, "description": "..."},
        ...
        "heuristic": False,
    }

while several consumers (the premium insight/coach/report endpoints, the tests,
and the frontend Zod schema) expect a *flat* dict:

    {"facial_harmony": 78.2, ...}

That mismatch caused a ``TypeError`` when sorting/comparing the nested dicts and
silently emptied the Pro/Elite features. This helper accepts either shape (and
``None``) and always returns flat float scores, so every reader stays robust.
"""

from typing import Any, Dict


def normalize_breakdown(breakdown: Any) -> Dict[str, float]:
    """Return ``{category: score}`` for both nested and flat breakdown shapes."""
    result: Dict[str, float] = {}
    if not isinstance(breakdown, dict):
        return result

    for key, value in breakdown.items():
        if key == "heuristic":
            continue
        if isinstance(value, dict):
            score = value.get("score")
            if isinstance(score, (int, float)) and not isinstance(score, bool):
                result[key] = float(score)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            result[key] = float(value)

    return result
