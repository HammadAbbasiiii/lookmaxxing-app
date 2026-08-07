"""
90-Day Action Plan Generator Service

Generates personalized 90-day transformation plans using:
- Category breakdown scores (6 categories from Step 7.2)
- DeepSeek AI for personalization (when available)
- Template-based fallback (when API unavailable)

Psychological principles embedded:
- Zeigarnik Effect: Small daily tasks, progress tracking
- Endowment Effect: Personalized to the user
- Loss Aversion: Streaks, progress bars
- Progress Principle: Small wins, milestone celebrations
- Peak-End Rule: Climactic phase endings with progress photo comparisons
"""

import logging
import uuid
import random
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Category → Task mapping tables
# ---------------------------------------------------------------------------

# Skin quality tasks by score tier
SKIN_TASKS = {
    "low": {  # 0-49
        "morning": [
            {"task": "Cleanse face with gentle foaming cleanser", "time": "AM", "duration_minutes": 2},
            {"task": "Apply lightweight moisturiser", "time": "AM", "duration_minutes": 1},
        ],
        "evening": [
            {"task": "Remove makeup/sunscreen with micellar water", "time": "PM", "duration_minutes": 2},
            {"task": "Cleanse with gentle cleanser", "time": "PM", "duration_minutes": 2},
            {"task": "Apply moisturiser", "time": "PM", "duration_minutes": 1},
        ],
        "weekly": [
            {"task": "Exfoliate with gentle AHA/BHA", "time": "PM", "duration_minutes": 5, "days": ["Monday", "Thursday"]},
        ],
        "products": [
            {"name": "Cerave Hydrating Cleanser", "price": "$15", "reason": "Gentle, non-stripping formula"},
            {"name": "The Ordinary Niacinamide 10%", "price": "$8", "reason": "Reduces inflammation and evens tone"},
            {"name": "La Roche-Posay Anthelios SPF 50", "price": "$30", "reason": "Essential sun protection"},
        ],
    },
    "medium": {  # 50-69
        "morning": [
            {"task": "Cleanse face with gentle cleanser", "time": "AM", "duration_minutes": 2},
            {"task": "Apply Vitamin C serum", "time": "AM", "duration_minutes": 1},
            {"task": "Apply moisturiser with SPF 30+", "time": "AM", "duration_minutes": 1},
        ],
        "evening": [
            {"task": "Double cleanse (oil cleanser + foam cleanser)", "time": "PM", "duration_minutes": 4},
            {"task": "Apply Niacinamide serum", "time": "PM", "duration_minutes": 1},
            {"task": "Apply night moisturiser", "time": "PM", "duration_minutes": 1},
        ],
        "weekly": [
            {"task": "Chemical exfoliation (AHA/BHA)", "time": "PM", "duration_minutes": 5, "days": ["Wednesday", "Sunday"]},
            {"task": "Clay mask for pores", "time": "PM", "duration_minutes": 15, "days": ["Saturday"]},
        ],
        "products": [
            {"name": "SkinCeuticals C E Ferulic", "price": "$160", "reason": "Professional-grade Vitamin C for brightness"},
            {"name": "Paula's Choice 2% BHA Liquid Exfoliant", "price": "$34", "reason": "Gentle daily chemical exfoliation"},
            {"name": "COSRX Snail Mucin Essence", "price": "$22", "reason": "Hydration and skin barrier repair"},
        ],
    },
    "high": {  # 70-89
        "morning": [
            {"task": "Gentle cleanse or water rinse", "time": "AM", "duration_minutes": 1},
            {"task": "Apply antioxidant serum (Vitamin C or Ferulic)", "time": "AM", "duration_minutes": 1},
            {"task": "Apply SPF 50+", "time": "AM", "duration_minutes": 1},
        ],
        "evening": [
            {"task": "Double cleanse", "time": "PM", "duration_minutes": 3},
            {"task": "Alternate: Retinol (Mon/Wed/Fri) or Peptide serum", "time": "PM", "duration_minutes": 1},
            {"task": "Apply eye cream", "time": "PM", "duration_minutes": 1},
            {"task": "Apply night cream", "time": "PM", "duration_minutes": 1},
        ],
        "weekly": [
            {"task": "Gentle chemical exfoliation", "time": "PM", "duration_minutes": 5, "days": ["Sunday"]},
        ],
        "products": [
            {"name": "SkinMedica TNS Eye Repair", "price": "$100", "reason": "Targeted eye area treatment"},
            {"name": "Sunday Riley Good Genes", "price": "$85", "reason": "Lactic acid for gentle refinement"},
        ],
    },
    "elite": {  # 90-100
        "morning": [
            {"task": "Water rinse or micellar water", "time": "AM", "duration_minutes": 1},
            {"task": "Apply antioxidant serum", "time": "AM", "duration_minutes": 1},
            {"task": "Apply SPF 50+ PA++++", "time": "AM", "duration_minutes": 1},
        ],
        "evening": [
            {"task": "Double cleanse", "time": "PM", "duration_minutes": 3},
            {"task": "Rotate: Retinol / Peptides / Recovery night", "time": "PM", "duration_minutes": 1},
            {"task": "Apply peptide eye cream", "time": "PM", "duration_minutes": 1},
            {"task": "Apply barrier-repair moisturiser", "time": "PM", "duration_minutes": 1},
        ],
        "weekly": [
            {"task": "Professional-grade enzyme mask", "time": "PM", "duration_minutes": 15, "days": ["Saturday"]},
        ],
        "products": [
            {"name": "SkinBetter Science Alto Defense Serum", "price": "$170", "reason": "Advanced antioxidant protection"},
            {"name": "Augustinus Bader The Rich Cream", "price": "$280", "reason": "Luxury barrier repair and renewal"},
        ],
    },
}

# Jawline definition exercises by tier
JAWLINE_TASKS = {
    "low": {
        "daily": [
            {"task": "Chewing gum (sugar-free, mastic) - 15 min each side", "time": "After lunch", "duration_minutes": 15},
            {"task": "Tongue posture practice (mewing) - roof of mouth", "time": "Throughout day", "duration_minutes": 0},
        ],
        "plus": [
            {"task": "Jaw opening resistance exercise - 3 sets x 10 reps", "time": "PM", "duration_minutes": 5},
            {"task": "Chin tucks for neck posture - 3 sets x 15 reps", "time": "PM", "duration_minutes": 3},
        ],
    },
    "medium": {
        "daily": [
            {"task": "Chewing mastic gum - 20 min", "time": "After lunch", "duration_minutes": 20},
            {"task": "Consistent tongue posture throughout the day", "time": "Throughout day", "duration_minutes": 0},
            {"task": "Gua sha facial massage (jawline focus)", "time": "AM or PM", "duration_minutes": 5},
        ],
        "plus": [
            {"task": "Jaw resistance training with Jawzrsize or similar", "time": "PM", "duration_minutes": 5},
        ],
    },
    "high": {
        "daily": [
            {"task": "Maintain correct tongue posture", "time": "Throughout day", "duration_minutes": 0},
            {"task": "Gua sha or jade roller massage", "time": "AM", "duration_minutes": 3},
        ],
        "plus": [
            {"task": "Facial yoga for jawline definition - 5 min routine", "time": "PM", "duration_minutes": 5},
        ],
    },
    "elite": {
        "daily": [
            {"task": "Maintain tongue posture and good head posture", "time": "Throughout day", "duration_minutes": 0},
            {"task": "Lymphatic drainage facial massage", "time": "AM", "duration_minutes": 3},
        ],
    },
}

# Eye area recommendations
EYE_TASKS = {
    "low": {
        "daily": [
            {"task": "Get 8 hours of sleep - no screens 30 min before bed", "time": "Night", "duration_minutes": 480},
            {"task": "Cold compress or chilled spoons on eyes - 5 min", "time": "AM", "duration_minutes": 5},
            {"task": "Reduce screen brightness and use blue light filter", "time": "Throughout day", "duration_minutes": 0},
        ],
        "products": [
            {"name": "The Ordinary Caffeine Solution 5%", "price": "$10", "reason": "Reduces puffiness and dark circles"},
            {"name": "CeraVe Eye Repair Cream", "price": "$14", "reason": "Gentle hydration for the eye area"},
        ],
    },
    "medium": {
        "daily": [
            {"task": "Prioritise 7-8 hours quality sleep", "time": "Night", "duration_minutes": 450},
            {"task": "Apply eye cream (caffeine + peptides)", "time": "AM and PM", "duration_minutes": 1},
        ],
        "weekly": [
            {"task": "Under-eye hydrogel masks - 15 min", "time": "PM", "duration_minutes": 15, "days": ["Wednesday", "Sunday"]},
        ],
        "products": [
            {"name": "Kiehl's Creamy Eye Treatment with Avocado", "price": "$34", "reason": "Deep hydration and smoothing"},
        ],
    },
    "high": {
        "daily": [
            {"task": "Maintain consistent sleep schedule", "time": "Night", "duration_minutes": 0},
            {"task": "Apply retinol eye cream (PM only)", "time": "PM", "duration_minutes": 1},
        ],
        "weekly": [
            {"task": "LED light therapy for eye area - 10 min", "time": "PM", "duration_minutes": 10, "days": ["Monday", "Thursday"]},
        ],
    },
    "elite": {
        "daily": [
            {"task": "Maintain excellent sleep hygiene", "time": "Night", "duration_minutes": 0},
            {"task": "Apply advanced peptide eye treatment", "time": "PM", "duration_minutes": 1},
        ],
    },
}

# Facial structure (structure, nose, chin) activities
STRUCTURE_TASKS = {
    "low": {
        "daily": [
            {"task": "Posture correction - shoulders back, chin parallel to floor", "time": "Throughout day", "duration_minutes": 0},
            {"task": "Neck stretches - 5 min routine", "time": "AM and PM", "duration_minutes": 5},
        ],
    },
    "medium": {
        "daily": [
            {"task": "Maintain correct posture while sitting and standing", "time": "Throughout day", "duration_minutes": 0},
            {"task": "Facial yoga routine for cheekbone lift", "time": "PM", "duration_minutes": 5},
        ],
    },
    "high": {
        "daily": [
            {"task": "Maintain excellent head and neck posture", "time": "Throughout day", "duration_minutes": 0},
            {"task": "Advanced facial yoga - 5 min", "time": "PM", "duration_minutes": 5},
        ],
    },
    "elite": {
        "daily": [
            {"task": "Maintain optimal posture as second nature", "time": "Throughout day", "duration_minutes": 0},
        ],
    },
}

# Core daily habits (everyone gets these)
CORE_HABITS = [
    {"task": "Drink 2-3 litres of water", "time": "Throughout day", "duration_minutes": 0, "category": "hydration"},
    {"task": "Eat protein with every meal", "time": "Meal times", "duration_minutes": 0, "category": "nutrition"},
    {"task": "Walk 8,000+ steps", "time": "Throughout day", "duration_minutes": 60, "category": "movement"},
    {"task": "No phone 30 min before bed", "time": "PM", "duration_minutes": 0, "category": "sleep"},
]


# ---------------------------------------------------------------------------
# Score tier helper
# ---------------------------------------------------------------------------
def _score_tier(score: float) -> str:
    """Map a 0-100 score to a tier label."""
    if score >= 90:
        return "elite"
    elif score >= 70:
        return "high"
    elif score >= 50:
        return "medium"
    else:
        return "low"


# ---------------------------------------------------------------------------
# Motivational content
# ---------------------------------------------------------------------------
MOTIVATIONAL_QUOTES = [
    {"day": 1, "quote": "The journey of a thousand miles begins with a single step. — Lao Tzu"},
    {"day": 7, "quote": "You've completed your first week. The habit is forming."},
    {"day": 14, "quote": "Two weeks in. Consistency beats intensity every time."},
    {"day": 21, "quote": "They say it takes 21 days to form a habit. Today, yours is set."},
    {"day": 30, "quote": "🎉 Phase 1 complete! Take your first progress photo today."},
    {"day": 37, "quote": "You're now in Phase 2 — where the real transformation begins."},
    {"day": 45, "quote": "Halfway through Phase 2. Look how far you've come."},
    {"day": 54, "quote": "Small daily actions compound into extraordinary results."},
    {"day": 60, "quote": "🎉 Day 60! Take your mid-point progress photo. The difference is real."},
    {"day": 67, "quote": "Final phase. These last 4 weeks cement your new identity."},
    {"day": 75, "quote": "You're not the same person who started 75 days ago."},
    {"day": 83, "quote": "One week from the finish line. Finish strong."},
    {"day": 90, "quote": "🏆 You did it. 90 days. This is your new baseline, not your peak."},
]

MILESTONES = {
    "day_7": {
        "title": "Week 1 Consistency Check",
        "message": "You've built the foundation. Notice how much easier the routine feels now?",
        "action": "Check how many days you completed your full routine.",
    },
    "day_14": {
        "title": "Habit Formation",
        "message": "Two weeks of consistency. Your brain is rewiring these into automatic behaviours.",
        "action": "Rate your energy levels and skin feel on a scale of 1-10.",
    },
    "day_21": {
        "title": "Habit Locked In",
        "message": "Research shows it takes 21 days to form a habit. Your routine should feel natural now.",
        "action": "Reflect: What's been the easiest part? The hardest?",
    },
    "day_30": {
        "title": "Phase 1 Complete — Progress Photo Day",
        "message": "Take your first progress photo. Even if changes are subtle, they are happening beneath the surface.",
        "action": "Upload a new photo for comparison with your Day 1 baseline.",
    },
    "day_45": {
        "title": "Mid-Phase 2 Check-in",
        "message": "You're deep in the building phase. This is where patience pays off.",
        "action": "Are you still consistent with your evening routine? Reassess and recommit.",
    },
    "day_60": {
        "title": "Phase 2 Complete — Mid-Point Transformation",
        "message": "Two-thirds through the journey. The changes should be visible, both in the mirror and in how you feel.",
        "action": "Upload your Day 60 progress photo. Compare with Day 1 and Day 30.",
    },
    "day_75": {
        "title": "Final Stretch",
        "message": "Only 15 days remain. Everything you've built is about to become permanent.",
        "action": "Identify one habit you want to keep for life beyond the 90 days.",
    },
    "day_90": {
        "title": "🏆 Transformation Complete",
        "message": "90 days. This is your transformation. But this is not the end – it's your new starting point.",
        "action": "Upload your final photo. See your full Before → During → After journey.",
    },
}

PHASE_COMPLETION_MESSAGES = {
    "phase_1": "🎉 You've built the foundation. Your routine is now a habit. Take your Day 30 photo and let's build on this momentum.",
    "phase_2": "🔥 Incredible progress. The daily effort is compounding. You're seeing real, visible change. Take your Day 60 photo and step into the mastery phase.",
    "phase_3": "🏆 You've transformed. This is not the end — this is your new baseline. The habits you've built will serve you for life. Your final photo shows how far you've come.",
}


# ---------------------------------------------------------------------------
# DeepSeek-enhanced plan personalisation
# ---------------------------------------------------------------------------
def _personalise_with_deepseek(
    category_breakdown: Dict[str, Any],
    score_data: Dict[str, Any],
    user_profile: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Attempt to personalise the plan using DeepSeek AI.
    Returns None if DeepSeek is unavailable (triggers fallback).
    """
    try:
        from app.services.deepseek_service import generate_personalized_content

        gender = user_profile.get("gender", "male")
        overall = score_data.get("score", score_data.get("overall_score", 70))

        # Find weakest and strongest categories
        cats = {}
        for key in ["facial_harmony", "skin_quality", "jawline_definition", "eye_appeal", "facial_structure", "masculinity_femininity"]:
            if key in category_breakdown:
                cats[key] = category_breakdown[key].get("score", 70)

        if cats:
            sorted_by_score = sorted(cats.items(), key=lambda x: x[1])
            weakest_categories = [name for name, _ in sorted_by_score[:3]]
            strongest = sorted_by_score[-1][0] if sorted_by_score else "facial_harmony"
        else:
            weakest_categories = ["skin_quality", "jawline_definition", "eye_appeal"]

        # Use existing DeepSeek service for personalised content
        response = generate_personalized_content(
            score=overall,
            gender=gender,
            weakest_categories=weakest_categories,
        )

        if response and response.get("success"):
            data = response.get("data", {})

            # Extract motivational messages from the personalised content
            motivational = data.get("motivational_message", "")

            # Split the long motivational message into phase-specific ones
            # The DeepSeek response gives one overall message; we adapt it for each phase
            phase_1_msg = f"Getting started: {motivational[:250]}" if motivational else PHASE_COMPLETION_MESSAGES["phase_1"]
            phase_2_msg = f"You're making real progress. {motivational[100:300]}" if len(motivational) > 100 else PHASE_COMPLETION_MESSAGES["phase_2"]
            phase_3_msg = f"Look how far you've come. {motivational[-200:]}" if len(motivational) > 200 else PHASE_COMPLETION_MESSAGES["phase_3"]

            # Extract category tips for bonus products
            bonus_products = []
            bonus_tip = ""
            tips = data.get("category_tips", [])
            if tips:
                for tip in tips[:2]:
                    prods = tip.get("recommended_products", [])
                    for prod in prods:
                        if isinstance(prod, str):
                            bonus_products.append({"name": prod, "price": "Varies", "reason": f"Recommended for {tip.get('category', 'improvement')}"})
                if tips:
                    first_tip = tips[0]
                    bonus_tip = f"{first_tip.get('category', 'Focus area')}: {'; '.join(first_tip.get('daily_actions', [])[:2])}"

            return {
                "phase_1_message": phase_1_msg,
                "phase_2_message": phase_2_msg,
                "phase_3_message": phase_3_msg,
                "bonus_products": bonus_products[:3],
                "bonus_tip": bonus_tip or "Consistency is the secret ingredient that outperforms any single product.",
            }
        return None
    except Exception as e:
        logger.warning(f"DeepSeek personalisation failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Build weekly tasks from category data
# ---------------------------------------------------------------------------
def _build_weekly_tasks(
    category_breakdown: Dict[str, Any],
    user_profile: Dict[str, Any],
    phase: str,
    week: int,
) -> List[Dict[str, Any]]:
    """Build the list of daily tasks for a given phase and week."""
    gender = user_profile.get("gender", "male")

    # Get tiers for each category
    skin_tier = _score_tier(category_breakdown.get("skin_quality", {}).get("score", 70))
    jaw_tier = _score_tier(category_breakdown.get("jawline_definition", {}).get("score", 70))
    eye_tier = _score_tier(category_breakdown.get("eye_appeal", {}).get("score", 70))
    structure_tier = _score_tier(category_breakdown.get("facial_structure", {}).get("score", 70))

    daily_tasks = []

    # --- Phase 1 (Days 1-30): Foundation — skincare, hydration, basic grooming ---
    if phase == "phase_1":
        # Core habits (everyone)
        for habit in CORE_HABITS:
            daily_tasks.append(habit.copy())

        # Skin care (morning + evening from mapping)
        skin_data = SKIN_TASKS.get(skin_tier, SKIN_TASKS["medium"])
        for task in skin_data.get("morning", []):
            daily_tasks.append(task.copy())
        for task in skin_data.get("evening", []):
            daily_tasks.append(task.copy())

        # If week >= 2, add weekly skin treatments
        if week >= 2:
            for task in skin_data.get("weekly", []):
                daily_tasks.append(task.copy())

        # Eye care basics if eye score is low/medium
        if eye_tier in ("low", "medium"):
            eye_data = EYE_TASKS.get(eye_tier, EYE_TASKS["medium"])
            for task in eye_data.get("daily", [])[:2]:
                daily_tasks.append(task.copy())

        # Grooming basics
        daily_tasks.append({"task": "Keep eyebrows groomed and tidy", "time": "Weekly", "duration_minutes": 10, "days": ["Sunday"]})
        daily_tasks.append({"task": "Maintain clean, styled hair", "time": "AM", "duration_minutes": 5})

    # --- Phase 2 (Days 31-60): Building — jawline, posture, advanced grooming, diet ---
    elif phase == "phase_2":
        # All core habits continue
        for habit in CORE_HABITS:
            daily_tasks.append(habit.copy())

        # Advanced skincare
        skin_data = SKIN_TASKS.get(skin_tier, SKIN_TASKS["medium"])
        for task in skin_data.get("evening", [])[-2:]:
            daily_tasks.append(task.copy())
        for task in skin_data.get("weekly", []):
            daily_tasks.append(task.copy())

        # Jawline exercises
        jaw_data = JAWLINE_TASKS.get(jaw_tier, JAWLINE_TASKS["medium"])
        for task in jaw_data.get("daily", []):
            daily_tasks.append(task.copy())
        for task in jaw_data.get("plus", []):
            daily_tasks.append(task.copy())

        # Posture work
        daily_tasks.append({"task": "Wall posture check - 2 min, back against wall", "time": "AM", "duration_minutes": 2})
        daily_tasks.append({"task": "Neck and shoulder stretch routine", "time": "PM", "duration_minutes": 5})

        # Diet refinement
        daily_tasks.append({"task": "Track protein intake - aim for 1.6g per kg bodyweight", "time": "Throughout day", "duration_minutes": 0})
        daily_tasks.append({"task": "Reduce processed sugar and fried foods", "time": "Throughout day", "duration_minutes": 0})

        # Eye care
        eye_data = EYE_TASKS.get(eye_tier, EYE_TASKS["medium"])
        if "weekly" in eye_data:
            for task in eye_data.get("weekly", []):
                daily_tasks.append(task.copy())

    # --- Phase 3 (Days 61-90): Mastery — maintenance, refinement, lifestyle integration ---
    elif phase == "phase_3":
        # Streamlined core habits
        daily_tasks.append(CORE_HABITS[0].copy())  # Water
        daily_tasks.append(CORE_HABITS[1].copy())  # Protein
        daily_tasks.append({"task": "Maintain 8,000+ steps daily", "time": "Throughout day", "duration_minutes": 0})

        # Refined skincare
        skin_data = SKIN_TASKS.get(skin_tier, SKIN_TASKS["high"])
        for task in skin_data.get("evening", [])[-1:]:
            daily_tasks.append(task.copy())

        # Jawline maintenance
        jaw_data = JAWLINE_TASKS.get(jaw_tier, JAWLINE_TASKS["high"])
        for task in jaw_data.get("daily", []):
            daily_tasks.append(task.copy())

        # Structure maintenance
        struct_data = STRUCTURE_TASKS.get(structure_tier, STRUCTURE_TASKS["high"])
        for task in struct_data.get("daily", []):
            daily_tasks.append(task.copy())

        # Lifestyle integration
        daily_tasks.append({"task": "Meditate or breathe deeply for 5 min", "time": "AM", "duration_minutes": 5})
        daily_tasks.append({"task": "Grooming maintenance - haircut, brow tidy, beard trim", "time": "Weekly", "duration_minutes": 20, "days": ["Saturday"]})

        # Professional consideration for low-tier categories
        if skin_tier == "low":
            daily_tasks.append({"task": "Research local dermatologists for professional consultation", "time": "This month", "duration_minutes": 30, "one_off": True})
        if jaw_tier == "low":
            daily_tasks.append({"task": "Consider orthodontic or maxillofacial consultation", "time": "This month", "duration_minutes": 30, "one_off": True})

    return daily_tasks


# ---------------------------------------------------------------------------
# Build product recommendations
# ---------------------------------------------------------------------------
def _build_product_recommendations(
    category_breakdown: Dict[str, Any],
    deepseek_personalisation: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Build product recommendations using the dedicated product recommendation engine.

    Falls back gracefully if the engine or product database is unavailable,
    using the hardcoded product lists from the task mapping tables.
    """
    try:
        from app.services.product_recommendation_service import get_product_recommendations as get_recs

        # Normalise category keys to what the engine expects
        # The plan generator uses e.g. "skin_quality", "eye_appeal", "jawline_definition",
        # "facial_structure", "facial_harmony", "masculinity_femininity".
        # The product engine uses "skin_quality", "jawline_definition", "eye_appeal",
        # "facial_structure", "grooming", "general".
        normalised = {}
        for key in ["skin_quality", "jawline_definition", "eye_appeal", "facial_structure"]:
            if key in category_breakdown:
                normalised[key] = category_breakdown[key].get("score", category_breakdown[key]) if isinstance(category_breakdown[key], dict) else category_breakdown[key]

        # Map facial_harmony / masculinity_femininity to grooming or general
        if "facial_harmony" in category_breakdown:
            score = category_breakdown["facial_harmony"].get("score") if isinstance(category_breakdown["facial_harmony"], dict) else category_breakdown["facial_harmony"]
            if "grooming" not in normalised:
                normalised["grooming"] = score

        if "masculinity_femininity" in category_breakdown:
            score = category_breakdown["masculinity_femininity"].get("score") if isinstance(category_breakdown["masculinity_femininity"], dict) else category_breakdown["masculinity_femininity"]
            if "general" not in normalised:
                normalised["general"] = score

        overall = None
        if "facial_harmony" in category_breakdown:
            overall = category_breakdown["facial_harmony"].get("score") if isinstance(category_breakdown["facial_harmony"], dict) else category_breakdown["facial_harmony"]

        raw_recs = get_recs(
            category_breakdown=normalised,
            overall_score=overall,
            max_products=8,
        )

        if raw_recs:
            # Convert to the plan generator's product format
            products = []
            for rec in raw_recs:
                prod = rec.get("product", {})
                products.append({
                    "name": prod.get("name", "Product"),
                    "brand": prod.get("brand", ""),
                    "price": f"${prod.get('price', 0):.0f}" if isinstance(prod.get("price"), (int, float)) else str(prod.get("price", "")),
                    "reason": rec.get("reason", "Recommended for your improvement areas"),
                    "rating": prod.get("rating"),
                    "reviews_count": prod.get("reviews_count"),
                    "tier": rec.get("tier", "mid_range"),
                    "affiliate_link": prod.get("affiliate_link"),
                    "image_url": prod.get("image_url"),
                    "category": rec.get("category", "general"),
                })
            return products[:8]

    except Exception as e:
        logger.warning(f"Product recommendation engine unavailable, using fallback: {e}")

    # ── Fallback: hardcoded products from task mapping tables ──
    products: List[Dict[str, Any]] = []

    cats = {}
    for key in ["facial_harmony", "skin_quality", "jawline_definition", "eye_appeal", "facial_structure", "masculinity_femininity"]:
        if key in category_breakdown:
            cats[key] = category_breakdown[key].get("score", 70)

    sorted_cats = sorted(cats.items(), key=lambda x: x[1])

    for cat_name, cat_score in sorted_cats[:3]:
        tier = _score_tier(cat_score)

        if cat_name == "skin_quality":
            for p in SKIN_TASKS.get(tier, SKIN_TASKS["medium"]).get("products", [])[:2]:
                products.append(p)
        elif cat_name == "eye_appeal":
            for p in EYE_TASKS.get(tier, EYE_TASKS.get("medium", {})).get("products", [])[:1]:
                products.append(p)
        elif cat_name == "jawline_definition":
            if tier in ("low", "medium"):
                products.append({"name": "Mastic Gum (Chios)", "price": "$15", "reason": "Natural jaw exercise — harder than regular gum"})
                products.append({"name": "Gua Sha Stone (Rose Quartz)", "price": "$12", "reason": "Facial massage tool for jawline definition"})
        elif cat_name == "facial_structure":
            if tier in ("low", "medium"):
                products.append({"name": "Posture Corrector Brace", "price": "$20", "reason": "Helps train proper neck and shoulder alignment"})

    if deepseek_personalisation and deepseek_personalisation.get("bonus_products"):
        products.extend(deepseek_personalisation["bonus_products"])

    seen = set()
    unique_products: List[Dict[str, Any]] = []
    for p in products:
        if p["name"] not in seen:
            seen.add(p["name"])
            unique_products.append(p)

    return unique_products[:8]


# ---------------------------------------------------------------------------
# Main plan generator
# ---------------------------------------------------------------------------
def generate_action_plan(
    score_data: Dict[str, Any],
    category_breakdown: Dict[str, Any],
    user_profile: Optional[Dict[str, Any]] = None,
    skip_deepseek: bool = False,
) -> Dict[str, Any]:
    """
    Generate a personalised 90-day transformation action plan.

    Args:
        score_data: dict with overall score (e.g. {"score": 72.5} or {"overall_score": 72.5})
        category_breakdown: dict with 6 category scores from face_analysis_service
        user_profile: dict with age, gender, goals (optional)
        skip_deepseek: if True, skip the DeepSeek API call entirely (instant template)

    Returns:
        Full 90-day plan dict with phases, tasks, milestones, products, motivational content.
    """
    if user_profile is None:
        user_profile = {}

    gender = user_profile.get("gender", "male")
    overall_score = score_data.get("score", score_data.get("overall_score", 70))

    plan_id = str(uuid.uuid4())

    # --- Attempt DeepSeek personalisation (skip if requested) ---
    if skip_deepseek:
        deepseek_personalisation = None
    else:
        deepseek_personalisation = _personalise_with_deepseek(category_breakdown, score_data, user_profile)

    # --- Build Phase 1 (Days 1-30) ---
    phase_1_weekly = []
    phase_1_themes = [
        (1, "Skincare Reset & Hydration", "Build the core skincare habit"),
        (2, "Routine Lock-in", "Morning and evening routines should feel automatic"),
        (3, "Nutrition Foundation", "Feed your skin and body from within"),
        (4, "Sleep & Recovery", "Your body transforms while you rest"),
    ]

    # Extend to 4 weeks (matching themes or repeating)
    for i in range(4):
        week_num = i + 1
        if i < len(phase_1_themes):
            _, theme, goal = phase_1_themes[i]
        else:
            _, theme, goal = phase_1_themes[-1]

        daily_tasks = _build_weekly_tasks(category_breakdown, user_profile, "phase_1", week_num)

        phase_1_weekly.append({
            "week": week_num,
            "theme": theme,
            "description": goal,
            "daily_tasks": daily_tasks,
        })

    # --- Build Phase 2 (Days 31-60) ---
    phase_2_weekly = []
    phase_2_themes = [
        (5, "Jawline & Posture Introduction", "Start the physical transformation work"),
        (6, "Advanced Skincare Layering", "Introduce actives and targeted treatments"),
        (7, "Diet & Exercise Refinement", "Optimise nutrition for facial definition"),
        (8, "Consistency Under Pressure", "Maintain routines even when life gets busy"),
    ]

    for i in range(4):
        week_num = i + 5
        if i < len(phase_2_themes):
            _, theme, goal = phase_2_themes[i]
        else:
            _, theme, goal = phase_2_themes[-1]

        daily_tasks = _build_weekly_tasks(category_breakdown, user_profile, "phase_2", week_num)

        phase_2_weekly.append({
            "week": week_num,
            "theme": theme,
            "description": goal,
            "daily_tasks": daily_tasks,
        })

    # --- Build Phase 3 (Days 61-90) ---
    phase_3_weekly = []
    phase_3_themes = [
        (9, "Refinement & Self-Assessment", "Identify what's working and double down"),
        (10, "Professional Integration", "Consider expert help for persistent concerns"),
        (11, "Lifestyle Lock-in", "Make these habits permanent"),
        (12, "Final Push & Celebration", "Finish strong with your Day 90 photo"),
    ]

    for i in range(4):
        week_num = i + 9
        if i < len(phase_3_themes):
            _, theme, goal = phase_3_themes[i]
        else:
            _, theme, goal = phase_3_themes[-1]

        daily_tasks = _build_weekly_tasks(category_breakdown, user_profile, "phase_3", week_num)

        phase_3_weekly.append({
            "week": week_num,
            "theme": theme,
            "description": goal,
            "daily_tasks": daily_tasks,
        })

    # --- Build products ---
    products = _build_product_recommendations(category_breakdown, deepseek_personalisation)

    # --- Build motivational quotes ---
    motivational_quotes = MOTIVATIONAL_QUOTES.copy()

    # --- Build milestone map ---
    milestones = {}
    for key, value in MILESTONES.items():
        milestones[key] = value

    # --- Phase messages (use DeepSeek personalisation if available) ---
    if deepseek_personalisation:
        phase_1_msg = deepseek_personalisation.get("phase_1_message", PHASE_COMPLETION_MESSAGES["phase_1"])
        phase_2_msg = deepseek_personalisation.get("phase_2_message", PHASE_COMPLETION_MESSAGES["phase_2"])
        phase_3_msg = deepseek_personalisation.get("phase_3_message", PHASE_COMPLETION_MESSAGES["phase_3"])
        bonus_tip = deepseek_personalisation.get("bonus_tip", "")
    else:
        phase_1_msg = PHASE_COMPLETION_MESSAGES["phase_1"]
        phase_2_msg = PHASE_COMPLETION_MESSAGES["phase_2"]
        phase_3_msg = PHASE_COMPLETION_MESSAGES["phase_3"]
        bonus_tip = "Consistency is your greatest advantage. Even 5 minutes a day compounds over 90 days."

    # --- Assemble full plan ---
    plan = {
        "plan_id": plan_id,
        "total_days": 90,
        "current_day": 0,
        "generated_at": datetime.utcnow().isoformat(),
        "generated_by": "deepseek" if deepseek_personalisation else "template",
        "phases": {
            "phase_1": {
                "days": "1-30",
                "title": "Foundation — Build Your Base",
                "emotional_goal": "Build trust and routine",
                "focus_areas": ["Skincare", "Hydration", "Sleep", "Basic Grooming"],
                "weekly_tasks": phase_1_weekly,
                "phase_completion_message": phase_1_msg,
            },
            "phase_2": {
                "days": "31-60",
                "title": "Building — Sculpt & Define",
                "emotional_goal": "Create momentum and visible change",
                "focus_areas": ["Jawline Exercises", "Posture", "Diet Refinement", "Advanced Grooming"],
                "weekly_tasks": phase_2_weekly,
                "phase_completion_message": phase_2_msg,
            },
            "phase_3": {
                "days": "61-90",
                "title": "Mastery — Refine & Excel",
                "emotional_goal": "Cement identity and pride",
                "focus_areas": ["Maintenance", "Refinement", "Professional Help", "Lifestyle Integration"],
                "weekly_tasks": phase_3_weekly,
                "phase_completion_message": phase_3_msg,
            },
        },
        "products": products,
        "motivational_quotes": motivational_quotes,
        "milestones": milestones,
        "bonus_tip": bonus_tip,
        "user_profile": {
            "gender": gender,
        },
    }

    return plan


# ---------------------------------------------------------------------------
# Fallback: template-only plan (no DeepSeek attempted)
# ---------------------------------------------------------------------------
def generate_fallback_plan(
    overall_score: float = 70.0,
    gender: str = "male",
) -> Dict[str, Any]:
    """
    Generate a generic template plan (used when DeepSeek is known to be unavailable,
    faster than calling _personalise_with_deepseek which will fail anyway).

    This produces the same structure as generate_action_plan but skips the API call.
    """
    # Create basic category breakdown at the overall score level
    category_breakdown = {
        "facial_harmony": {"score": overall_score, "description": "Based on overall analysis"},
        "skin_quality": {"score": overall_score, "description": "Based on overall analysis"},
        "jawline_definition": {"score": overall_score, "description": "Based on overall analysis"},
        "eye_appeal": {"score": overall_score, "description": "Based on overall analysis"},
        "facial_structure": {"score": overall_score, "description": "Based on overall analysis"},
        "masculinity_femininity": {"score": overall_score, "description": "Based on overall analysis"},
    }

    return generate_action_plan(
        score_data={"score": overall_score},
        category_breakdown=category_breakdown,
        user_profile={"gender": gender},
        skip_deepseek=True,
    )
