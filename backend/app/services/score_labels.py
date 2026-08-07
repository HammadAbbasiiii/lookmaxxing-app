"""
Score Labeling System
Maps numerical scores (0-100) to tier labels with emoji and descriptions.

Used across:
- Dashboard: Show user's overall and per-category labels
- Photo analysis: Label each category score in the breakdown
- Plan generator: Set difficulty expectations based on score tier
- iOS widget/notification layer: Display motivational tier labels
"""
from typing import Dict


def get_score_label(score: float) -> Dict[str, object]:
    """
    Map a 0-100 score to a tier label.

    Args:
        score: Numeric score from 0 to 100.

    Returns:
        dict with:
          - label (str): Human-readable tier name
          - emoji (str): Emoji icon for the tier
          - description (str): One-line explanation
          - tier (int): Numeric tier 0-4 for sorting/logic
    """
    score = max(0.0, min(100.0, score))

    if score >= 90:
        return {
            "label": "Apex",
            "emoji": "👑",
            "description": "Elite-level features — among the top tier",
            "tier": 4,
        }
    elif score >= 85:
        return {
            "label": "Outstanding",
            "emoji": "🌟",
            "description": "Exceptional quality with minimal room for improvement",
            "tier": 4,
        }
    elif score >= 75:
        return {
            "label": "High Appeal",
            "emoji": "💫",
            "description": "Well above average — commanding presence",
            "tier": 3,
        }
    elif score >= 65:
        return {
            "label": "Great",
            "emoji": "✨",
            "description": "Solid above-average features with growth potential",
            "tier": 2,
        }
    elif score >= 55:
        return {
            "label": "Good",
            "emoji": "👍",
            "description": "Healthy baseline with clear room to improve",
            "tier": 1,
        }
    elif score >= 40:
        return {
            "label": "Average",
            "emoji": "📈",
            "description": "Good foundation — focused effort will pay off",
            "tier": 0,
        }
    elif score >= 25:
        return {
            "label": "Developing",
            "emoji": "🔧",
            "description": "Early stage — consistent effort will yield visible gains",
            "tier": 0,
        }
    else:
        return {
            "label": "Beginner",
            "emoji": "🌱",
            "description": "Starting point — transformative potential ahead",
            "tier": 0,
        }


def get_score_tier_name(tier: int) -> str:
    """Convert a numeric tier back to its canonical label."""
    return {4: "Apex", 3: "High Appeal", 2: "Great", 1: "Good", 0: "Developing"}.get(tier, "Beginner")